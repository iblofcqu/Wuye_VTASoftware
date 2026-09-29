declare module 'plotly.js-dist-min' {
  interface PlotlyApi {
    newPlot(
      root: HTMLElement,
      data: unknown[],
      layout?: Record<string, unknown>,
      config?: Record<string, unknown>,
    ): Promise<unknown>
    react(
      root: HTMLElement,
      data: unknown[],
      layout?: Record<string, unknown>,
      config?: Record<string, unknown>,
    ): Promise<unknown>
    purge(root: HTMLElement): void
  }

  const Plotly: PlotlyApi
  export default Plotly
}
