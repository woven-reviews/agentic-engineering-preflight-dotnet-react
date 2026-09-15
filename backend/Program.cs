using Microsoft.EntityFrameworkCore;
using Preflight.Api.Data;

var builder = WebApplication.CreateBuilder(args);
builder.Services.AddControllers();
// "localhost" and "127.0.0.1" are different browser origins even though they reach the same
// server, so both need to be allowed for local dev regardless of which one a developer types.
string[] corsOrigins = builder.Configuration["Cors:AllowedOrigin"] is { } configuredOrigin
    ? [configuredOrigin]
    : ["http://localhost:5173", "http://127.0.0.1:5173"];
builder.Services.AddCors(options => options.AddDefaultPolicy(policy => policy.WithOrigins(corsOrigins).AllowAnyHeader().AllowAnyMethod()));
builder.Services.AddDbContext<AppDbContext>(options => options.UseNpgsql(builder.Configuration.GetConnectionString("DefaultConnection")));
builder.Services.AddOpenApi();

var app = builder.Build();

// Applies migrations automatically on startup so `docker compose up` "just works" with no
// separate seed/migrate step — there's no seed data for this trivial preflight app.
using (var scope = app.Services.CreateScope())
{
    var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
    await db.Database.MigrateAsync();
}

app.MapOpenApi();
app.UseCors();
app.MapGet("/health", () => Results.Ok(new { status = "ok" }));
app.MapControllers();
app.Run();

public partial class Program;
