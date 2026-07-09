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
using System.Collections.Generic;
using CommunityToolkit.Mvvm.ComponentModel;

namespace IDSImaging.Peak.Examples.AvaloniaSimpleLive.ViewModels;

/// <summary>
///     Abstract base class for all camera parameters displayed in the settings panel.
///     Subclasses hold the value and type-specific bindings; this base class handles
///     the name, enabled state, and the periodic update cycle.
/// </summary>
public abstract partial class CameraParameter : ObservableObject
{
    /// <summary>Controls whether the parameter control is interactive in the UI.</summary>
    [ObservableProperty] private bool _isEnabled = true;

    /// <summary>Display name shown in the UI.</summary>
    [ObservableProperty] private string _name = string.Empty;

    /// <summary>
    ///     Optional delegate that returns the current enabled state.
    ///     Called on each <see cref="Update" /> tick. If null, <see cref="IsEnabled" /> is not changed.
    /// </summary>
    public Func<bool>? UpdateEnabledState { get; init; }

    /// <summary>
    ///     Refreshes the enabled state from <see cref="UpdateEnabledState" />.
    ///     Subclasses override this to also refresh their value and range.
    /// </summary>
    public virtual void Update()
    {
        if (UpdateEnabledState != null)
        {
            IsEnabled = UpdateEnabledState();
        }
    }
}

/// <summary>
///     A numeric camera parameter (double or integer) with a slider and a spin box.
///     Includes min/max range and an optional increment.
/// </summary>
public partial class DoubleOrIntegerParameter : CameraParameter
{
    private bool _isSyncing;

    /// <summary>Step increment. Currently informational; not enforced by the slider.</summary>
    [ObservableProperty] private double _inc;

    /// <summary>Maximum allowed value. Updated from hardware on each tick.</summary>
    [ObservableProperty] private double _max;

    /// <summary>Minimum allowed value. Updated from hardware on each tick.</summary>
    [ObservableProperty] private double _min;

    /// <summary>Current value, bound to both the slider and the numeric up-down control.</summary>
    [ObservableProperty] private double _value;

    /// <summary>Unit label shown below the slider (e.g. "µs", "fps", "x").</summary>
    public string? Unit { get; set; }

    /// <summary>Delegate that returns the current value from the hardware.</summary>
    public Func<double>? UpdateValue { get; init; }

    /// <summary>Delegate that returns (min, max, inc) from the hardware.</summary>
    public Func<(double, double, double)>? UpdateRange { get; init; }

    /// <summary>Called when the user changes the value. Use to write back to the hardware.</summary>
    public Action<double>? ValueChanged { get; init; }

    public override void Update()
    {
        base.Update();

        // prevent updates while we update
        _isSyncing = true;

        try
        {
            if (UpdateRange != null)
            {
                (Min, Max, Inc) = UpdateRange();
            }

            if (UpdateValue != null)
            {
                Value = UpdateValue();
            }
        }
        finally
        {
            _isSyncing = false;
        }
    }

    partial void OnValueChanged(double value)
    {
        if (_isSyncing)
        {
            return;
        }

        ValueChanged?.Invoke(value);
    }
}

/// <summary>
///     A camera parameter backed by a GenICam enumeration node, displayed as a combo box.
/// </summary>
public partial class EnumerationParameter : CameraParameter
{
    private bool _isSyncing;

    /// <summary>All available entry names for this enumeration.</summary>
    [ObservableProperty] private List<string> _entries = [];

    /// <summary>Currently selected entry name.</summary>
    [ObservableProperty] private string _value = string.Empty;

    /// <summary>Called when the user selects a different entry.</summary>
    public Action<string>? ValueChanged { get; init; }

    /// <summary>Delegate that returns the current entry name from the hardware.</summary>
    public Func<string>? UpdateValue { get; init; }

    public override void Update()
    {
        base.Update();

        // prevent updates while we update
        _isSyncing = true;

        try
        {
            if (UpdateValue != null)
            {
                Value = UpdateValue();
            }
        }
        finally
        {
            _isSyncing = false;
        }
    }

    partial void OnValueChanged(string value)
    {
        if (_isSyncing)
        {
            return;
        }

        ValueChanged?.Invoke(value);
    }
}

/// <summary>
///     A camera parameter backed by a GenICam string node, displayed as a text box.
/// </summary>
public partial class StringParameter : CameraParameter
{
    private bool _isSyncing;

    /// <summary>Current string value.</summary>
    [ObservableProperty] private string _value = string.Empty;

    /// <summary>Called when the user edits the value.</summary>
    public Action<string>? ValueChanged { get; init; }

    /// <summary>Delegate that returns the current value from the hardware.</summary>
    public Func<string>? UpdateValue { get; init; }

    public override void Update()
    {
        base.Update();

        // prevent updates while we update
        _isSyncing = true;

        try
        {
            if (UpdateValue != null)
            {
                Value = UpdateValue();
            }
        }
        finally
        {
            _isSyncing = false;
        }
    }

    partial void OnValueChanged(string value)
    {
        if (_isSyncing)
        {
            return;
        }

        ValueChanged?.Invoke(value);
    }
}

/// <summary>
///     A camera parameter backed by a GenICam boolean node, displayed as a checkbox.
/// </summary>
public partial class BooleanParameter : CameraParameter
{
    private bool _isSyncing;

    /// <summary>Current boolean value.</summary>
    [ObservableProperty] private bool _value;

    /// <summary>Called when the user toggles the value.</summary>
    public Action<bool>? ValueChanged { get; init; }

    /// <summary>Delegate that returns the current value from the hardware.</summary>
    public Func<bool>? UpdateValue { get; init; }

    public override void Update()
    {
        base.Update();

        // prevent updates while we update
        _isSyncing = true;

        try
        {
            if (UpdateValue != null)
            {
                Value = UpdateValue();
            }
        }
        finally
        {
            _isSyncing = false;
        }
    }

    partial void OnValueChanged(bool value)
    {
        if (_isSyncing)
        {
            return;
        }

        ValueChanged?.Invoke(value);
    }
}
