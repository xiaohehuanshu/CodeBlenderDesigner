import { create } from "zustand";

type DisplayValue = string | number | boolean;
type BriefFieldMap = Record<string, DisplayValue>;
type AssetKind = "glb" | "script" | "trace";

interface GenerateRequest {
  user_input: string;
  session_id?: string;
  thread_id?: string;
  image_dir?: string | null;
  markdown_path?: string | string[] | null;
  geometry_context_path?: string | null;
  blend_file?: string | null;
  output_dir?: string | null;
  validate_generated_script?: boolean;
  auto_execute_generated_script?: boolean;
  export_glb?: boolean;
}

interface GenerateResponse {
  session_id: string;
  thread_id: string;
  route_decision: string | null;
  should_end: boolean;
  generated_script_path: string | null;
  glb_path: string | null;
  execution_log: string[];
  errors: string[];
  trace_path: string | null;
  consolidated_prompt: string | null;
  refined_design_brief: string | null;
  design_brief_base_values?: unknown;
  runtime_validation_status?: string | null;
  runtime_validation_mode?: string | null;
}

type WsEvent =
  | {
      event: "connected";
      session_id: string;
    }
  | {
      event: "generation.start";
      session_id: string;
    }
  | {
      event: "generation.complete";
      session_id: string;
      route_decision?: string;
      glb_path?: string;
    }
  | {
      event: "generation.error";
      session_id: string;
      error: string;
    };

interface AppState {
  userInput: string;
  briefFields: BriefFieldMap;
  modelUrl: string | null;
  scriptUrl: string | null;
  traceUrl: string | null;
  isLoading: boolean;
  currentNode: string;
  logs: string[];
  errors: string[];
  sessionId: string;
  consolidatedPrompt: string | null;
  refinedDesignBrief: string | null;
  routeDecision: string | null;
  generatedScriptPath: string | null;
  tracePath: string | null;
  runtimeValidationStatus: string | null;
  runtimeValidationMode: string | null;
  wsConnected: boolean;

  setUserInput: (text: string) => void;
  setCurrentNode: (node: string) => void;
  addLog: (entry: string) => void;
  addError: (entry: string) => void;
  clearLogs: () => void;
  applyGenerateResult: (res: GenerateResponse) => void;
  applyWsEvent: (event: WsEvent) => void;
  runGenerate: (
    userInput: string,
    overrides?: Omit<GenerateRequest, "user_input">,
  ) => Promise<GenerateResponse>;
  disconnectSession: () => void;
  reset: () => void;
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

let ws: WebSocket | null = null;
let wsSessionId: string | null = null;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function normalizeDisplayValue(value: unknown): DisplayValue | null {
  if (
    typeof value === "string" ||
    typeof value === "number" ||
    typeof value === "boolean"
  ) {
    return value;
  }
  return null;
}

function normalizeBriefFields(value: unknown): BriefFieldMap {
  if (!isRecord(value)) {
    return {};
  }

  const normalized: BriefFieldMap = {};
  for (const [key, rawValue] of Object.entries(value)) {
    const displayValue = normalizeDisplayValue(rawValue);
    if (displayValue !== null) {
      normalized[key] = displayValue;
    }
  }
  return normalized;
}

function appendEntry(entries: string[], entry: string): string[] {
  const normalized = entry.trim();
  if (!normalized) {
    return entries;
  }
  if (entries.at(-1) === normalized) {
    return entries;
  }
  return [...entries, normalized];
}

function buildAssetUrl(
  kind: AssetKind,
  sessionId: string,
  assetPath: string | null | undefined,
): string | null {
  if (!sessionId || !assetPath) {
    return null;
  }
  return `${API_BASE}/${kind}/${encodeURIComponent(sessionId)}?v=${Date.now()}`;
}

async function readErrorMessage(res: Response): Promise<string> {
  const raw = await res.text();
  if (!raw) {
    return `Request failed with status ${res.status}`;
  }

  try {
    const parsed = JSON.parse(raw);
    if (typeof parsed?.detail === "string" && parsed.detail.trim()) {
      return parsed.detail;
    }
  } catch {
    // Fall back to the raw response body.
  }

  return raw;
}

function formatError(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return String(error);
}

async function requestGenerate(payload: GenerateRequest): Promise<GenerateResponse> {
  const res = await fetch(`${API_BASE}/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    throw new Error(await readErrorMessage(res));
  }

  return res.json();
}

function closeSessionSocket() {
  if (ws) {
    ws.close();
    ws = null;
  }
  wsSessionId = null;
}

function openSessionSocket(sessionId: string) {
  if (
    ws &&
    wsSessionId === sessionId &&
    (ws.readyState === WebSocket.OPEN ||
      ws.readyState === WebSocket.CONNECTING)
  ) {
    return;
  }

  closeSessionSocket();

  const url = API_BASE.replace(/^http/, "ws") + `/ws/${encodeURIComponent(sessionId)}`;
  wsSessionId = sessionId;
  ws = new WebSocket(url);

  ws.onopen = () => {
    useStore.setState({ wsConnected: true });
  };

  ws.onmessage = (event) => {
    try {
      const message: WsEvent = JSON.parse(event.data);
      useStore.getState().applyWsEvent(message);
    } catch {
      // Ignore unexpected messages from the backend.
    }
  };

  ws.onerror = () => {
    useStore.getState().addError("WebSocket 连接异常");
  };

  ws.onclose = () => {
    ws = null;
    wsSessionId = null;
    useStore.setState({ wsConnected: false });
  };
}

export const useStore = create<AppState>((set, get) => ({
  userInput: "",
  briefFields: {},
  modelUrl: null,
  scriptUrl: null,
  traceUrl: null,
  isLoading: false,
  currentNode: "",
  logs: [],
  errors: [],
  sessionId: "",
  consolidatedPrompt: null,
  refinedDesignBrief: null,
  routeDecision: null,
  generatedScriptPath: null,
  tracePath: null,
  runtimeValidationStatus: null,
  runtimeValidationMode: null,
  wsConnected: false,

  setUserInput: (text) => set({ userInput: text }),

  setCurrentNode: (node) => set({ currentNode: node }),

  addLog: (entry) =>
    set((state) => ({
      logs: appendEntry(state.logs, entry),
    })),

  addError: (entry) =>
    set((state) => ({
      errors: appendEntry(state.errors, entry),
    })),

  clearLogs: () => set({ logs: [], errors: [] }),

  applyGenerateResult: (res) =>
    set({
      isLoading: false,
      sessionId: res.session_id,
      routeDecision: res.route_decision,
      generatedScriptPath: res.generated_script_path,
      tracePath: res.trace_path,
      consolidatedPrompt: res.consolidated_prompt,
      refinedDesignBrief: res.refined_design_brief,
      runtimeValidationStatus: res.runtime_validation_status ?? null,
      runtimeValidationMode: res.runtime_validation_mode ?? null,
      currentNode: "生成完成",
      modelUrl: buildAssetUrl("glb", res.session_id, res.glb_path),
      scriptUrl: buildAssetUrl(
        "script",
        res.session_id,
        res.generated_script_path,
      ),
      traceUrl: buildAssetUrl("trace", res.session_id, res.trace_path),
      briefFields: normalizeBriefFields(res.design_brief_base_values),
      logs: res.execution_log.filter((entry) => entry.trim()),
      errors: res.errors.filter((entry) => entry.trim()),
    }),

  applyWsEvent: (event) => {
    switch (event.event) {
      case "connected":
        set({ sessionId: event.session_id, wsConnected: true });
        break;
      case "generation.start":
        set({ isLoading: true, currentNode: "正在启动生成管线…" });
        get().addLog("▶ 开始生成");
        break;
      case "generation.complete":
        set((state) => ({
          isLoading: false,
          currentNode: "生成完成",
          routeDecision: event.route_decision ?? state.routeDecision,
          modelUrl: event.glb_path
            ? buildAssetUrl("glb", event.session_id, event.glb_path)
            : state.modelUrl,
        }));
        get().addLog("✔ 生成完成");
        if (event.glb_path) {
          get().addLog(`✔ GLB: ${event.glb_path}`);
        }
        break;
      case "generation.error":
        set({ isLoading: false, currentNode: "生成失败" });
        get().addError(event.error);
        break;
    }
  },

  runGenerate: async (userInput, overrides = {}) => {
    const trimmedInput = userInput.trim();
    if (!trimmedInput) {
      throw new Error("请输入设计需求");
    }

    const currentSessionId = get().sessionId;
    const sessionId = overrides.session_id ?? currentSessionId ?? `session_${Date.now()}`;

    set((state) => ({
      isLoading: true,
      userInput: trimmedInput,
      sessionId,
      currentNode: "准备生成…",
      logs: [`用户: ${trimmedInput}`],
      errors: [],
      routeDecision: state.routeDecision,
      modelUrl: state.modelUrl,
      scriptUrl: state.scriptUrl,
      traceUrl: state.traceUrl,
      briefFields: state.briefFields,
    }));

    openSessionSocket(sessionId);

    try {
      const res = await requestGenerate({
        user_input: trimmedInput,
        session_id: sessionId,
        ...overrides,
      });
      get().applyGenerateResult(res);
      return res;
    } catch (error) {
      const message = formatError(error);
      set({ isLoading: false, currentNode: "生成失败" });
      get().addError(message);
      throw error;
    }
  },

  disconnectSession: () => {
    closeSessionSocket();
    set({ wsConnected: false });
  },

  reset: () => {
    closeSessionSocket();
    set({
      userInput: "",
      briefFields: {},
      modelUrl: null,
      scriptUrl: null,
      traceUrl: null,
      isLoading: false,
      currentNode: "",
      logs: [],
      errors: [],
      sessionId: "",
      consolidatedPrompt: null,
      refinedDesignBrief: null,
      routeDecision: null,
      generatedScriptPath: null,
      tracePath: null,
      runtimeValidationStatus: null,
      runtimeValidationMode: null,
      wsConnected: false,
    });
  },
}));
