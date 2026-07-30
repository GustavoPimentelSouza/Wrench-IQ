interface PlaceholderPageProps {
  titulo: string;
}

export function PlaceholderPage({ titulo }: PlaceholderPageProps) {
  return (
    <div>
      <h2 className="text-lg font-semibold text-gray-900">{titulo}</h2>
      <p className="mt-2 text-sm text-gray-500">Em construção.</p>
    </div>
  );
}
