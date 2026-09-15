FROM mcr.microsoft.com/dotnet/sdk:10.0
WORKDIR /src
COPY Preflight.Api.csproj ./
COPY Tests/Preflight.Api.Tests.csproj Tests/
RUN dotnet restore
RUN dotnet restore Tests/Preflight.Api.Tests.csproj
COPY . ./
RUN dotnet build --no-restore
EXPOSE 8080
CMD ["dotnet", "watch", "run", "--no-launch-profile", "--no-hot-reload"]
