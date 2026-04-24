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
using System.Drawing;
using System.Threading;
using System.Windows.Forms;

using ICVImage = IDSImaging.Peak.ICV.Types.Image;

namespace IDSImaging.Peak.Examples.SimpleLiveWindowsForms
{
    internal class SimplePictureBox : PictureBox
    {
        private readonly Mutex _mutex = new Mutex();
        private ICVImage? _icvImage = null;

        public new ICVImage? Image
        {
            get => _icvImage;
            set => SetImage(value);
        }

        private void SetImage(ICVImage? image)
        {
            // Updates the displayed image from a background thread.
            // A mutex is used to synchronize access with the UI thread (OnPaint),
            // preventing concurrent reads/writes to the Image property.
            // If the mutex is not immediately available, the incoming image is discarded
            // to avoid blocking and to keep rendering responsive.
            if (_mutex.WaitOne(0))
            {
                // Dispose of previous image before assigning the new one
                if (_icvImage != null)
                {
                    _icvImage.Dispose();
                    _icvImage = null;
                }
                _icvImage = image;

                Bitmap? bitmap = null;

                if (_icvImage != null)
                {
                    var width = Convert.ToInt32(_icvImage.Width);
                    var height = Convert.ToInt32(_icvImage.Height);
                    var stride = Convert.ToInt32(_icvImage.SizeInBytes / height);

                    var data = _icvImage.Data;

                    // Note: Microsoft PixelFormat.Format32bppRgb expects colors in the order blue, green, red, alpha.
                    bitmap = new Bitmap(width, height, stride,
                        System.Drawing.Imaging.PixelFormat.Format32bppRgb, data);
                }

                // Dispose of previous image before assigning the new one
                if (base.Image != null)
                {
                    base.Image.Dispose();
                    base.Image = null;
                }
                base.Image = bitmap;

                _mutex.ReleaseMutex();
            }
            else
            {
                // Drop the frame if the UI thread is currently painting
                image?.Dispose();
            }
        }

        protected override void OnPaint(PaintEventArgs pe)
        {
            // Ensure exclusive access to the Image while it is being rendered,
            // preventing it from being modified or disposed concurrently.
            _mutex.WaitOne();
            base.OnPaint(pe);
            _mutex.ReleaseMutex();
        }
    }
}
