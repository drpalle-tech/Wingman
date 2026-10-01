using System.Net.Http;
using System.Net.Http.Json;

namespace Shop;

public record Order(int Id, decimal Total);

public class OrderService
{
    public Order? GetOrder(int id)
    {
        var client = new HttpClient();
        var response = client.GetAsync($"https://api.example.com/orders/{id}").Result;
        response.EnsureSuccessStatusCode();
        return response.Content.ReadFromJsonAsync<Order>().Result;
    }
}
