using System;

namespace Trading;

public static class PriceFeed
{
    public static event EventHandler<decimal>? PriceChanged;

    public static void Publish(decimal price) => PriceChanged?.Invoke(null, price);
}

public class PriceWidget
{
    private decimal _lastPrice;

    public PriceWidget()
    {
        PriceFeed.PriceChanged += OnPriceChanged;
    }

    public decimal LastPrice => _lastPrice;

    private void OnPriceChanged(object? sender, decimal price)
    {
        _lastPrice = price;
    }
}
