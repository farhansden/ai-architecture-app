import type { GenerateApiResult } from '@/components/ResultPanel';

function trimBase(base: string): string {
  return base.trim().replace(/\/+$/, '');
}

/** Unify /generate vs /generate_visual_floor_plan payloads for ResultPanel. */
export function normalizeGenerateResponse(raw: Record<string, unknown>): GenerateApiResult {
  const parsed = raw.parsed_data as Record<string, unknown> | undefined;
  const projectFromParsed =
    parsed && typeof parsed === 'object'
      ? (Object.fromEntries(
          Object.entries(parsed).filter(([k]) => !String(k).startsWith('_')),
        ) as Record<string, unknown>)
      : {};

  const projectData = (raw.project_data ?? projectFromParsed) as Record<string, unknown>;

  return {
    floors: (raw.floors ?? raw.per_floor_svgs ?? {}) as Record<string, string>,
    layout_data: (raw.layout_data ?? raw.per_floor_layouts ?? {}) as Record<string, unknown>,
    design_reasoning: String(raw.design_reasoning ?? parsed?._design_reasoning ?? ''),
    validation: String(raw.validation ?? parsed?._validation ?? ''),
    maket_deliverable: (raw.maket_deliverable ?? projectData.maket_deliverable) as
      GenerateApiResult['maket_deliverable'],
    project_data: projectData,
    dxf_paths: raw.dxf_paths as GenerateApiResult['dxf_paths'],
    floors_3d: (raw.floors_3d ?? raw.per_floor_3d) as Record<string, string> | undefined,
    ground_floor_3d: raw.ground_floor_3d as string | undefined,
    renderer_3d_used: raw.renderer_3d_used as boolean | undefined,
    scores: raw.scores as GenerateApiResult['scores'],
    ground_score: raw.ground_score as GenerateApiResult['ground_score'],
    scorer_used: raw.scorer_used as boolean | undefined,
    floors_generated: Number(raw.floors_generated ?? 1),
    rooms_placed: Number(raw.rooms_placed ?? 0),
    rooms_failed: (raw.rooms_failed ?? []) as string[],
    warnings: (raw.warnings ?? []) as string[],
    per_floor_svgs: raw.per_floor_svgs as Record<string, string> | undefined,
    per_floor_3d: raw.per_floor_3d as Record<string, string> | undefined,
    ground_floor_svg: raw.ground_floor_svg as string | undefined,
  };
}

export async function requestFloorPlanGeneration(
  prompt: string,
  apiBase: string,
): Promise<GenerateApiResult> {
  const base = trimBase(apiBase || 'http://localhost:8000');

  let res = await fetch(`${base}/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt }),
  });

  if (res.status === 404) {
    res = await fetch(`${base}/generate_visual_floor_plan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt, output_dir: 'outputs/' }),
    });
  }

  if (!res.ok) {
    const text = await res.text();
    let detail = text;
    try {
      detail = JSON.parse(text)?.detail ?? text;
    } catch {
      /* keep raw body */
    }
    throw new Error(detail || `Server error ${res.status}`);
  }

  const data = (await res.json()) as Record<string, unknown>;
  return normalizeGenerateResponse(data);
}
