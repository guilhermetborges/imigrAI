import { PageState } from "@/components/states/page-state";

export default function Loading(): JSX.Element {
  return (
    <PageState
      title="Carregando interface"
      description="Aguarde alguns segundos enquanto preparamos sua jornada."
    />
  );
}
