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
using System.Globalization;
using Avalonia.Data.Converters;

namespace IDSImaging.Peak.Examples.AvaloniaSimpleLive.Utils;

public class InvariantDoubleConverter : IValueConverter
{
    public object Convert(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        if (value is not double d)
        {
            return parameter != null ? $"{parameter}-" : "-";
        }

        var label = parameter?.ToString() ?? "";
        return $"{label}{d.ToString("F2", CultureInfo.InvariantCulture)}";
    }

    public object ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        // This converter is intended for one-way display binding only.
        // ConvertBack is implemented for completeness but not expected to be called.
        return double.TryParse(value?.ToString(), NumberStyles.Any, CultureInfo.InvariantCulture, out var result)
            ? result
            : 0.0;
    }
}
