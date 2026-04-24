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

using System.ComponentModel;
using System.Drawing;
using System.Windows.Forms;
using Image = IDSImaging.Peak.ICV.Types.Image;

namespace IDSImaging.Peak.Examples.SimpleLiveWindowsForms
{
    public sealed class FormWindow : Form
    {
        private readonly Camera _camera;
        private Label _infoLabel;
        private Label? _labelAcquisitionStatistics;
        private Panel? _labelPanel;
        private SimplePictureBox? _pictureBox;

        public FormWindow()
        {
            var projectName = "simple_live_windows_forms";
            var version = "v1.3.1";

            InitializeComponent();

            _infoLabel!.Text = $"{projectName} {version}";
            Text = projectName;
            FormClosing += FormWindow_FormClosing;

            // Open first available camera, connect events and start the acquisition
            _camera = Camera.OpenFirstAvailable();
            _camera.ImageReceived += CameraImageReceived;
            _camera.AcquisitionStatisticsChanged += CameraAcquisitionStatisticsChanged;
            _camera.StartAcquisition();
        }

        private void CameraImageReceived(object sender, Image image)
        {
            // Update the display picture box with the acquired image
            if (_pictureBox != null)
            {
                _pictureBox.Image = image;
            }
        }

        private void CameraAcquisitionStatisticsChanged(object sender, uint frameCounter, uint errorCounter)
        {
            // Update the acquisition statistics label
            // Note: This event is raised from a non-UI thread, so we must marshal the update
            // to the UI thread using BeginInvoke to safely access the control.
            _labelAcquisitionStatistics?.BeginInvoke((MethodInvoker) (() =>
                _labelAcquisitionStatistics.Text = $"Frames acquired: {frameCounter}, errors: {errorCounter}"));
        }

        private void FormWindow_FormClosing(object? sender, FormClosingEventArgs e)
        {
            // Stop acquisition and clean up our unmanaged resources
            _camera.StopAcquisition();
            _camera.Dispose();
        }

        private void InitializeComponent()
        {
            _pictureBox = new SimplePictureBox();
            _labelPanel = new Panel();
            _infoLabel = new Label();
            _labelAcquisitionStatistics = new Label();
            ((ISupportInitialize) _pictureBox).BeginInit();
            _labelPanel.SuspendLayout();
            SuspendLayout();
            //
            // pictureBox
            //
            _pictureBox.Dock = DockStyle.Top;
            _pictureBox.Location = new Point(0, 0);
            _pictureBox.Name = "_pictureBox";
            _pictureBox.Size = new Size(700, 437);
            _pictureBox.SizeMode = PictureBoxSizeMode.Zoom;
            _pictureBox.TabIndex = 1;
            _pictureBox.TabStop = false;
            //
            // labelPanel
            //
            _labelPanel.Controls.Add(_infoLabel);
            _labelPanel.Controls.Add(_labelAcquisitionStatistics);
            _labelPanel.Dock = DockStyle.Bottom;
            _labelPanel.Location = new Point(0, 435);
            _labelPanel.Name = "_labelPanel";
            _labelPanel.Size = new Size(700, 15);
            _labelPanel.TabIndex = 2;
            //
            // infoLabel
            //
            _infoLabel.AutoSize = true;
            _infoLabel.Dock = DockStyle.Right;
            _infoLabel.Location = new Point(596, 0);
            _infoLabel.Name = "_infoLabel";
            _infoLabel.Size = new Size(104, 13);
            _infoLabel.TabIndex = 2;
            _infoLabel.Text = "Projectname Version";
            //
            // counterLabel
            //
            _labelAcquisitionStatistics.AutoSize = true;
            _labelAcquisitionStatistics.Dock = DockStyle.Left;
            _labelAcquisitionStatistics.Location = new Point(0, 0);
            _labelAcquisitionStatistics.Name = "_labelAcquisitionStatistics";
            _labelAcquisitionStatistics.Size = new Size(69, 13);
            _labelAcquisitionStatistics.TabIndex = 1;
            _labelAcquisitionStatistics.Text = "counterLabel";
            //
            // FormWindow
            //
            ClientSize = new Size(700, 450);
            Controls.Add(_labelPanel);
            Controls.Add(_pictureBox);
            Name = "FormWindow";
            Text = "Projectname";
            ((ISupportInitialize) _pictureBox).EndInit();
            _labelPanel.ResumeLayout(false);
            _labelPanel.PerformLayout();
            ResumeLayout(false);
        }
    }
}
