export default function Orb3D() {
  return (
    <div className="orb-shell" aria-hidden="true">
      <div className="orb-shadow" />
      <div className="orb-ring orb-ring-outer" />
      <div className="orb-ring orb-ring-mid" />
      <div className="orb-core">
        <div className="orb-wave orb-wave-back" />
        <div className="orb-wave orb-wave-front" />
        <div className="orb-highlight" />
        <div className="orb-center" />
      </div>
    </div>
  );
}
