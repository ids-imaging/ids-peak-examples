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
using System.Linq;

using IDSImaging.Peak.API;
using IDSImaging.Peak.API.Core;
using Image = IDSImaging.Peak.ICV.Types.Image;

namespace IDSImaging.Peak.Examples.SimpleLiveWindowsForms
{
    internal class Camera : IDisposable
    {
        // Event which is raised if the counters has changed
        public delegate void CounterChangedEventHandler(object sender, uint frameCounter, uint errorCounter);

        // Event which is raised if a new image was received
        public delegate void ImageReceivedEventHandler(object sender, Image image);

        private readonly AcquisitionEngine _acquisitionEngine;
        private readonly DataStream _dataStream;

        // Note: _device must be kept so the GC does not delete it
        private readonly Device _device;
        private readonly NodeMap _nodeMapRemoteDevice;

        private Camera(Device device)
        {
            _device = device;
            _dataStream = _device.DataStreams().FirstOrDefault()?.OpenDataStream() ??
                          throw new Exception("Could not open data stream!");
            _nodeMapRemoteDevice = _device.RemoteDevice().NodeMaps().FirstOrDefault() ??
                                   throw new Exception("Could not get remote device node map!");

            // Create acquisition worker thread that waits for new images from the camera
            _acquisitionEngine = new AcquisitionEngine(_dataStream, _nodeMapRemoteDevice);

            // Propagate events to event subscribers
            _acquisitionEngine.ImageReceived += (sender, image) => ImageReceived?.Invoke(sender, image);
            _acquisitionEngine.CounterChanged += (sender, frameCounter, errorCounter) =>
                AcquisitionStatisticsChanged?.Invoke(sender, frameCounter, errorCounter);
        }

        public void Dispose()
        {
            // Make sure to stop the asynchronous acquisition worker
            // before disposing the device objects
            _acquisitionEngine.Stop();

            _acquisitionEngine.Dispose();
            _dataStream.Dispose();
            _nodeMapRemoteDevice.Dispose();
        }

        public event ImageReceivedEventHandler? ImageReceived;
        public event CounterChangedEventHandler? AcquisitionStatisticsChanged;

        public static Camera OpenFirstAvailable()
        {
            // Create instance of the device manager
            var deviceManager = DeviceManager.Instance();

            // Update the device manager
            deviceManager.Update();

            // Return if no device was found
            if (deviceManager.Devices().IsEmpty)
            {
                throw new Exception("No device found!");
            }

            // Open the first openable device in the device manager's device list
            var deviceCount = deviceManager.Devices().Count;
            for (var i = 0; i < deviceCount; ++i)
            {
                if (!deviceManager.Devices()[i].IsOpenable())
                {
                    continue;
                }

                return new Camera(deviceManager.Devices()[i].OpenDevice(DeviceAccessType.Control));
            }

            throw new Exception("No openable device found!");
        }

        public void StartAcquisition()
        {
            _acquisitionEngine.Start();
        }

        public void StopAcquisition()
        {
            _acquisitionEngine.Stop();
        }
    }
}
