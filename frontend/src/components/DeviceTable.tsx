import { Device, Health } from "@/lib/types";
import { HealthBadge } from "./HealthBadge";

type Props = {
  devices: Device[];
  health: Map<number, Health>;
  selected: Set<number>;
  onToggle: (id: number) => void;
};

export function DeviceTable({ devices, health, selected, onToggle }: Props) {
  return (
    <table cellPadding={6} style={{ borderCollapse: "collapse", width: "100%" }}>
      <thead>
        <tr style={{ background: "#f4f4f4", textAlign: "left" }}>
          <th></th>
          <th>Name</th>
          <th>IP</th>
          <th>Health</th>
          <th>Last checked</th>
        </tr>
      </thead>
      <tbody>
        {devices.map((d) => {
          const h = health.get(d.id);
          return (
            <tr key={d.id} style={{ borderTop: "1px solid #eee" }}>
              <td>
                <input
                  type="checkbox"
                  checked={selected.has(d.id)}
                  onChange={() => onToggle(d.id)}
                />
              </td>
              <td>{d.name}</td>
              <td>{d.ip_address}</td>
              <td><HealthBadge status={h?.status ?? "unknown"} /></td>
              <td style={{ fontSize: 12, color: "#666" }}>
                {h?.last_checked_at ?? "-"}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
