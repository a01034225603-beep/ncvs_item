import { Device, MatrixCell } from "@/lib/types";

type Props = { devices: Device[]; cells: MatrixCell[] };

export function Matrix({ devices, cells }: Props) {
  const lookup = new Map<string, MatrixCell>();
  for (const c of cells) lookup.set(`${c.src_bacs_id}-${c.dst_bacs_id}`, c);

  return (
    <table cellPadding={4} style={{ borderCollapse: "collapse" }}>
      <thead>
        <tr>
          <th></th>
          {devices.map((d) => (
            <th key={d.id} style={{ writingMode: "vertical-rl", fontSize: 11 }}>
              {d.name}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {devices.map((src) => (
          <tr key={src.id}>
            <td style={{ fontSize: 11, fontWeight: 600 }}>{src.name}</td>
            {devices.map((dst) => {
              if (src.id === dst.id)
                return <td key={dst.id} style={{ background: "#222" }} />;
              const cell = lookup.get(`${src.id}-${dst.id}`);
              const color = cell
                ? cell.status === "ok"
                  ? "#2ecc71"
                  : "#e74c3c"
                : "#bdc3c7";
              return (
                <td
                  key={dst.id}
                  title={cell?.error_message ?? cell?.tested_at ?? "no data"}
                  style={{ background: color, width: 16, height: 16 }}
                />
              );
            })}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
