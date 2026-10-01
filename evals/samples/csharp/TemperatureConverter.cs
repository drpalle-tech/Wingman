using System;

namespace Weather;

public static class TemperatureConverter
{
    private const double AbsoluteZeroCelsius = -273.15;

    public static double CelsiusToFahrenheit(double celsius)
    {
        if (double.IsNaN(celsius))
        {
            throw new ArgumentException("Temperature must be a number.", nameof(celsius));
        }

        if (celsius < AbsoluteZeroCelsius)
        {
            throw new ArgumentOutOfRangeException(nameof(celsius), celsius, "Temperature cannot be below absolute zero.");
        }

        return celsius * 9 / 5 + 32;
    }

    public static double FahrenheitToCelsius(double fahrenheit)
    {
        if (double.IsNaN(fahrenheit))
        {
            throw new ArgumentException("Temperature must be a number.", nameof(fahrenheit));
        }

        var celsius = (fahrenheit - 32) * 5 / 9;
        if (celsius < AbsoluteZeroCelsius)
        {
            throw new ArgumentOutOfRangeException(nameof(fahrenheit), fahrenheit, "Temperature cannot be below absolute zero.");
        }

        return celsius;
    }
}
