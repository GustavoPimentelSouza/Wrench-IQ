interface MetricCardProps {
  titulo: string;
  valor: string;
  tonalidade?: "padrao" | "alerta";
}

export function MetricCard({ titulo, valor, tonalidade = "padrao" }: MetricCardProps) {
  return (
    <div className="rounded-2xl bg-stone-50 px-6 py-5">
      <p className="mb-2 text-sm text-gray-500">{titulo}</p>
      <p
        className={`text-3xl font-semibold ${
          tonalidade === "alerta" ? "text-rose-800" : "text-gray-900"
        }`}
      >
        {valor}
      </p>
    </div>
  );
}
