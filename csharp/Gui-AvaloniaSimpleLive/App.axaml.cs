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
using Avalonia;
using Avalonia.Controls.ApplicationLifetimes;
using Avalonia.Markup.Xaml;
using Avalonia.Threading;
using IDSImaging.Peak.Examples.AvaloniaSimpleLive.Models;
using IDSImaging.Peak.Examples.AvaloniaSimpleLive.ViewModels;
using IDSImaging.Peak.Examples.AvaloniaSimpleLive.Views;
using MsBox.Avalonia;
using MsBox.Avalonia.Base;
using MsBox.Avalonia.Enums;

namespace IDSImaging.Peak.Examples.AvaloniaSimpleLive;

public class App : Application
{
    public override void Initialize()
    {
        AvaloniaXamlLoader.Load(this);
    }

    public override void OnFrameworkInitializationCompleted()
    {
        if (ApplicationLifetime is not IClassicDesktopStyleApplicationLifetime desktop)
        {
            return;
        }

        InitializeApp(desktop);
    }

    // async void is intentional here: OnFrameworkInitializationCompleted does not
    // support async, and all exceptions are caught inside the method itself.
    private static async void InitializeApp(IClassicDesktopStyleApplicationLifetime desktop)
    {
        try
        {
            var service = new CameraService();
            var vm = new CameraViewModel(service);

            var devices = service.GetCameraList().Where(x => x.Openable).ToList();

            desktop.MainWindow = new MainWindow { DataContext = vm };
            desktop.MainWindow.Closed += (_, _) =>
            {
                vm.StopUpdateTask();
                service.Dispose();
            };

            var dialogService = new FileDialogService(desktop.MainWindow);
            vm.SetFileDialogService(dialogService);

            if (devices.Count != 1)
            {
                // Show the main window first so the selection dialog has an owner.
                // If exactly one openable camera is found, skip the dialog entirely.
                desktop.MainWindow.Show();

                Dispatcher.UIThread.Post(async void () =>
                {
                    try
                    {
                        var dialog = new CameraSelectionWindow(service);

                        CameraInfo? selectedCamera = await dialog.ShowDialog<CameraInfo?>(desktop.MainWindow);
                        if (dialog.ViewModel != null)
                        {
                            await dialog.ViewModel.StopPollingAsync();
                        }

                        if (selectedCamera == null)
                        {
                            desktop.Shutdown();
                            return;
                        }

                        service.OpenCamera(selectedCamera);

                        var (width, height) = service.ImageDimensions();
                        vm.Initialize(width, height, CameraViewModel.GetPixelFormat(service.OutputPixelFormat));
                        service.StartCapture();
                        vm.TriggerUpdate();
                    }
                    catch (Exception)
                    {
                        desktop.Shutdown();
                    }

                }, DispatcherPriority.Background); // Background priority ensures layout completes first
            }
            else
            {
                service.OpenCamera(devices[0]);
                var (width, height) = service.ImageDimensions();
                vm.Initialize(width, height, CameraViewModel.GetPixelFormat(service.OutputPixelFormat));
                service.StartCapture();
                vm.TriggerUpdate();
            }
        }
        catch (Exception ex)
        {
            IMsBox<ButtonResult> box =
                MessageBoxManager.GetMessageBoxStandard("Error", $"Initialization failed: {ex.Message}");
            await box.ShowAsync();

            desktop.Shutdown();
        }
    }
}
