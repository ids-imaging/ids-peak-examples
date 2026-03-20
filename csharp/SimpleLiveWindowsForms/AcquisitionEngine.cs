// Copyright (C) 2026, IDS Imaging Development Systems GmbH.
//
// Permission to use, copy, modify, and/or distribute this software for
// any purpose with or without fee is hereby granted.
//
// THE SOFTWARE IS PROVIDED “AS IS” AND THE AUTHOR DISCLAIMS ALL
// WARRANTIES WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES
// OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE
// FOR ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY
// DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN
// AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
// OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

using System;
using System.Threading;

using IDSImaging.Peak.API.Core;
using IDSImaging.Peak.API.Core.Nodes;
using IDSImaging.Peak.API.Exceptions;
using IDSImaging.Peak.Common.Types;
using IDSImaging.Peak.ICV.Pipeline;

using Buffer = IDSImaging.Peak.API.Core.Buffer;
using ICVImage = IDSImaging.Peak.ICV.Types.Image;

namespace IDSImaging.Peak.Samples.SimpleLiveWindowsForms
{
    public class AcquisitionEngine : IDisposable
    {
        // Event which is raised if the counters has changed
        public delegate void CounterChangedEventHandler(object sender, uint frameCounter, uint errorCounter);
        public event CounterChangedEventHandler? CounterChanged;

        // Event which is raised if a new image was received
        public delegate void ImageReceivedEventHandler(object sender, ICVImage image);
        public event ImageReceivedEventHandler? ImageReceived;

        private readonly DataStream _dataStream;
        private readonly DefaultPipeline _pipeline;
        private readonly NodeMap _remoteDeviceNodeMap;

        private Thread? _acquisitionThread;
        private CancellationTokenSource? _cancellationTokenSource;
        private bool _acquisitionRunning;

        private uint _errorCounter;
        private uint _frameCounter;

        public AcquisitionEngine(DataStream dataStream, NodeMap remoteDeviceNodeMap)
        {
            _dataStream = dataStream;
            _remoteDeviceNodeMap = remoteDeviceNodeMap;

            _pipeline = new DefaultPipeline();
            _pipeline.OutputPixelFormat = PixelFormat.BGRa8;
        }

        private uint FrameCounter
        {
            get => _frameCounter;
            set
            {
                _frameCounter = value;
                InvokeCounterChangedEvent();
            }
        }

        private uint ErrorCounter
        {
            get => _errorCounter;
            set
            {
                _errorCounter = value;
                InvokeCounterChangedEvent();
            }
        }

        public void Dispose()
        {
            GC.SuppressFinalize(this);
            _pipeline.Dispose();
        }

        private void InvokeCounterChangedEvent()
        {
            // Raise event with current frame and error counter
            CounterChanged?.Invoke(this, _frameCounter, _errorCounter);
        }

        private void PrepareAcquisition()
        {
            // To prepare for untriggered continuous image acquisition, load the default user set if available
            // and wait until execution is finished
            try
            {
                _remoteDeviceNodeMap.FindNode<EnumerationNode>("UserSetSelector").SetCurrentEntry("Default");
                _remoteDeviceNodeMap.FindNode<CommandNode>("UserSetLoad").Execute();
                _remoteDeviceNodeMap.FindNode<CommandNode>("UserSetLoad").WaitUntilDone();
            }
            catch
            {
                // UserSet is not available
            }

            // Get the payload size for correct buffer allocation
            var payloadSize = Convert.ToUInt32(_remoteDeviceNodeMap.FindNode<IntegerNode>("PayloadSize").Value());

            // Get the minimum number of buffers that must be announced
            var minBuffersRequired = _dataStream.NumBuffersAnnouncedMinRequired();

            // Allocate and announce image buffers and queue them
            for (var bufferCount = 0; bufferCount < minBuffersRequired; ++bufferCount)
            {
                Buffer? buffer = _dataStream.AllocAndAnnounceBuffer(payloadSize, IntPtr.Zero);
                _dataStream.QueueBuffer(buffer);
            }
        }

        private void RevokeBuffers()
        {
            // Discard all buffers and free memory
            _dataStream.Flush(DataStreamFlushMode.DiscardAll);
            foreach (Buffer? buffer in _dataStream.AnnouncedBuffers())
            {
                _dataStream.RevokeBuffer(buffer);
            }
        }

        public void Start()
        {
            if (_acquisitionRunning)
            {
                return;
            }

            PrepareAcquisition();

            // Lock critical features to prevent them from changing during acquisition
            _remoteDeviceNodeMap.FindNode<IntegerNode>("TLParamsLocked").SetValue(1);

            // Start acquisition
            _dataStream.StartAcquisition();
            _remoteDeviceNodeMap.FindNode<CommandNode>("AcquisitionStart").Execute();
            _remoteDeviceNodeMap.FindNode<CommandNode>("AcquisitionStart").WaitUntilDone();

            // Start the thread running the acquisition loop
            _cancellationTokenSource = new CancellationTokenSource();
            _acquisitionThread = new Thread(() => AcquisitionLoop(_cancellationTokenSource.Token));
            _acquisitionThread.Start();

            _acquisitionRunning = true;
        }

        public void Stop()
        {
            if (!_acquisitionRunning)
            {
                return;
            }

            _cancellationTokenSource?.Cancel();

            try
            {
                // Try to stop the acquisition. This might fail if the device was disconnected.
                _remoteDeviceNodeMap.FindNode<CommandNode>("AcquisitionStop").Execute();
                _remoteDeviceNodeMap.FindNode<CommandNode>("AcquisitionStop").WaitUntilDone();
            }
            catch
            {
                // ignored
            }

            _dataStream.KillWait();
            _dataStream.StopAcquisition();

            // Wait until the acquisition worker thread has finished
            _acquisitionThread?.Join();

            try
            {
                _remoteDeviceNodeMap.FindNode<IntegerNode>("TLParamsLocked").SetValue(0);
            }
            catch
            {
                // ignored
            }

            RevokeBuffers();

            _acquisitionRunning = false;
        }

        private void AcquisitionLoop(CancellationToken cancellationToken)
        {
            while (!cancellationToken.IsCancellationRequested)
            {
                try
                {
                    // Get buffer from device's datastream
                    Buffer? buffer = _dataStream.WaitForFinishedBuffer(1000);

                    // The image still uses the underlying memory of `buffer`
                    using var icvImage = new ICVImage(buffer.ToImageView());

                    // Debayering and convert IDS peak ICV Image to displayable format
                    ICVImage convertedImage = _pipeline.Process(icvImage);

                    // Queue buffer so that it can be used again
                    _dataStream.QueueBuffer(buffer);

                    if (ImageReceived != null)
                    {
                        ImageReceived(this, convertedImage);
                    }
                    else
                    {
                        convertedImage.Dispose();
                    }

                    FrameCounter++;
                }
                catch (ApiAbortedException)
                {
                    // Gracefully handle exception caused by dataStream.KillWait()
                    return;
                }
                catch (Exception)
                {
                    ErrorCounter++;
                }
            }
        }
    }
}
