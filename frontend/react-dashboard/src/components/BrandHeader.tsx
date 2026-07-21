export function BrandHeader() {
  return (
    <header
      className="cog-header"
      style={{
        background:
          "linear-gradient(90deg, #000048 0%, #0A0A6A 55%, #1A1B7A 100%)",
      }}
    >
      <div className="cog-header-inner">
        <img
          src="/cog_logo.jpg"
          alt="Cognizant"
          className="cog-header-logo"
          draggable={false}
          style={{ mixBlendMode: "lighten" }}
        />
        <span className="cog-header-divider" aria-hidden="true" />
        {/* <span className="cog-header-product">Outage Communication System</span> */}
      </div>
      <div
        className="cog-header-accent"
        aria-hidden="true"
        style={{
          background:
            "linear-gradient(90deg, #06C7CC 0%, #2E308E 50%, #06C7CC 100%)",
        }}
      />
    </header>
  );
}
