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
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
      <table className="min-w-full divide-y divide-slate-200">
        <thead className="bg-slate-50">
          <tr className="text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
            <th className="w-10 px-4 py-3"></th>
            <th className="px-4 py-3">Name</th>
            <th className="px-4 py-3">IP</th>
            <th className="px-4 py-3">Health</th>
            <th className="px-4 py-3">Last checked</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 text-sm">
          {devices.map((d) => {
            const h = health.get(d.id);
            return (
              <tr key={d.id} className="hover:bg-slate-50">
                <td className="px-4 py-3">
                  <input
                    type="checkbox"
                    checked={selected.has(d.id)}
                    onChange={() => onToggle(d.id)}
                    className="h-4 w-4 rounded border-slate-300 text-slate-900 focus:ring-slate-500"
                  />
                </td>
                <td className="px-4 py-3 font-medium text-slate-900">
                  {d.name}
                </td>
                <td className="px-4 py-3 text-slate-600">{d.ip_address}</td>
                <td className="px-4 py-3">
                  <HealthBadge status={h?.status ?? "unknown"} />
                </td>
                <td className="px-4 py-3 text-xs text-slate-500">
                  {h?.last_checked_at ?? "-"}
                </td>
              </tr>
            );
          })}
          {devices.length === 0 && (
            <tr>
              <td colSpan={5} className="px-4 py-8 text-center text-sm text-slate-500">
                등록된 BACS 장비가 없습니다.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
