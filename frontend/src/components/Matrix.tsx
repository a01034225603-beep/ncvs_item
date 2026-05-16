import { Device, MatrixCell } from "@/lib/types";

type Props = { devices: Device[]; cells: MatrixCell[] };

export function Matrix({ devices, cells }: Props) {
  const lookup = new Map<string, MatrixCell>();
  for (const c of cells) lookup.set(`${c.src_bacs_id}-${c.dst_bacs_id}`, c);

  return (
    <div className="inline-block rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <table className="border-collapse">
        <thead>
          <tr>
            <th></th>
            {devices.map((d) => (
              <th
                key={d.id}
                className="px-1 align-bottom text-[11px] font-medium text-slate-600 [writing-mode:vertical-rl]"
              >
                {d.name}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {devices.map((src) => (
            <tr key={src.id}>
              <td className="pr-2 text-[11px] font-semibold text-slate-700">
                {src.name}
              </td>
              {devices.map((dst) => {
                if (src.id === dst.id) {
                  return (
                    <td
                      key={dst.id}
                      className="h-5 w-5 bg-slate-800"
                    />
                  );
                }
                const cell = lookup.get(`${src.id}-${dst.id}`);
                const cls = cell
                  ? cell.status === "ok"
                    ? "bg-emerald-500"
                    : "bg-red-500"
                  : "bg-slate-200";
                return (
                  <td
                    key={dst.id}
                    title={cell?.error_message ?? cell?.tested_at ?? "no data"}
                    className={`h-5 w-5 ${cls}`}
                  />
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
