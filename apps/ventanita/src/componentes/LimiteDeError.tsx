import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface Estado {
  error: Error | null;
}

/**
 * Si App lanza al montar o al renderizar, React desmonta todo y la ventana
 * queda muda y sin salida. Esto lo atrapa y lo muestra en pantalla, en la
 * voz de Remi (ley 3: sin culpa, sin pánico), con el detalle técnico debajo
 * para poder arreglarlo.
 */
export class LimiteDeError extends Component<Props, Estado> {
  state: Estado = { error: null };

  static getDerivedStateFromError(error: Error): Estado {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("[ventanita] crash en render:", error, info.componentStack);
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div className="ventanita ventanita--error">
        <p className="display-it voz">Algo se me rompió. No es culpa tuya.</p>
        <pre className="code limite-error__detalle">
          {this.state.error.name}: {this.state.error.message}
        </pre>
      </div>
    );
  }
}
