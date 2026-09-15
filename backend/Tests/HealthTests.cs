using System.Net;
using Microsoft.AspNetCore.Mvc.Testing;
using Xunit;

namespace Preflight.Api.Tests;

/// <summary>
/// Note: Program.cs applies EF Core migrations unconditionally on startup (by design, so
/// `docker compose up` needs no separate seed/migrate step), so even this /health-only test
/// needs a reachable Postgres via the ConnectionStrings__DefaultConnection environment
/// variable / configuration for the app to boot at all inside WebApplicationFactory.
/// </summary>
public sealed class HealthTests
{
    [Fact]
    public async Task Health_ReturnsOkStatus()
    {
        using var factory = new WebApplicationFactory<Program>();
        var client = factory.CreateClient();

        var response = await client.GetAsync("/health");

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var body = await response.Content.ReadAsStringAsync();
        Assert.Equal("{\"status\":\"ok\"}", body);
    }
}
