using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Preflight.Api.Data;
using Preflight.Api.Models;

namespace Preflight.Api.Controllers;

[ApiController]
[Route("api/v1/preflight")]
public sealed class PreflightController(AppDbContext db) : ControllerBase
{
    /// <summary>Round-trips through EF Core to Postgres: writes a row, then counts it back.</summary>
    [HttpGet("db-check")]
    public async Task<IActionResult> DbCheck()
    {
        db.Pings.Add(new Ping());
        await db.SaveChangesAsync();
        var count = await db.Pings.CountAsync();
        return Ok(new { database = "ok", pings = count });
    }
}
