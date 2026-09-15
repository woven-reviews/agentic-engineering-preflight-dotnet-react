namespace Preflight.Api.Models;

public sealed class Ping
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public string Note { get; set; } = "ok";
}
