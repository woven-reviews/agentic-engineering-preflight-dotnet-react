using Microsoft.EntityFrameworkCore;
using Preflight.Api.Models;

namespace Preflight.Api.Data;

public sealed class AppDbContext(DbContextOptions<AppDbContext> options) : DbContext(options)
{
    public DbSet<Ping> Pings => Set<Ping>();
}
