import { create } from "zustand";

type ParamValue = string | number | boolean;
type ModelParams = Record<string, ParamValue>;
type AssetKind = "glb" | "stl";

interface GenerateRequest {
  user_input: string;
  session_id?: string;
  thread_id?: string;
  image_dir?: string | null;
  markdown_path?: string | null;
  geometry_context_path?: string | null;
  blend_file?: string | null;
  output_dir?: string | null;
  validate_generated_script?: boolean;
  auto_execute_generated_script?: boolean;
  export_glb?: boolean;
  export_stl?: boolean;
}

interface GenerateResponse {
  session_id: string;
  thread_id: string;
  route_decision: string | null;
  should_end: boolean;
  generated_script_path: string | null;
  glb_path: string | null;
  stl_path: string | null;
  execution_log: string[];
  errors: string[];
  trace_path: string | null;
  consolidated_prompt: string | null;
  refined_design_brief: string | null;
  model_params?: unknown;
  design_brief_base_values?: unknown;
}

interface UpdateParamsRequest {
  session_id: string;
  params: ModelParams;
  blend_file?: string | null;
  output_dir?: string | null;
}

interface UpdateParamsResponse {
  session_id?: string;
  glb_path: string | null;
  stl_path: string | null;
  status: string;
  message?: string;
  model_params?: unknown;
  design_brief_base_values?: unknown;
}

type WsEvent =
  | { event: "connected"; session_id: string }
  | { event: "generation.start"; session_id: string }
  | { event: "generation.complete"; session_id: string; route_decision?: string; glb_path?: string; stl_path?: string }
  | { event: "generation.error"; session_id: string; error: string }
  | { event: "update_params.start"; session_id: string }
  | { event: "update_params.complete"; session_id: string; glb_path?: string; stl_path?: string }
  | { event: "update_params.error"; session_id: string; error: string };

interface AppState {
  userInput: string;
  modelParams: ModelParams;
  modelUrl: string | null;
  stlUrl: string | null;
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
  wsConnected: boolean;

  setUserInput: (text: string) => void;
  setCurrentNode: (node: string) => void;
  addLog: (entry: string) => void;
  addError: (entry: string) => void;
  clearLogs: () => void;
  setModelParams: (params: ModelParams) => void;
  updateParam: (key: string, value: ParamValue) => void;
  applyGenerateResult: (res: GenerateResponse) => void;
  applyUpdateParamsResult: (res: UpdateParamsResponse, patch?: ModelParams) => void;
  applyWsEvent: (event: WsEvent) => void;
  runGenerate: (userInput: string, overrides?: Omit<GenerateRequest, "user_input">) => Promise<GenerateResponse>;
  runUpdateParams: (params: ModelParams, overrides?: Omit<UpdateParamsRequest, "session_id" | "params">) => Promise<UpdateParamsResponse>;
  disconnectSession: () => void;
  reset: () => void;
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

let ws: WebSocket | null = null;
let wsSessionId: string | null = null;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function normalizeParamValue(value: unknown): ParamValue | null {
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return value;
  }
  return null;
}

function normalizeModelParams(value: unknown): ModelParams {
  if (!isRecord(value)) {
    return {};
  }

  const normalized: ModelParams = {};

  for (const [key, rawValue] of Object.entries(value)) {
    const paramValue = normalizeParamValue(rawValue);
    if (paramValue !== null) {
      normalized[key] = paramValue;
    }
  }

  return normalized;
}

function extractModelParams(payload: { model_params?: unknown; design_brief_base_values?: unknown }): ModelParams {
  const explicitParams = normalizeModelParams(payload.model_params);
  if (Object.keys(explicitParams).length > 0) {
    return explicitParams;
  }
  return normalizeModelParams(payload.design_brief_base_values);
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

function buildAssetUrl(kind: AssetKind, sessionId: string, assetPath: string | null | undefined): string | null {
  if (!sessionId || !assetPath) {
    return null;
  }
  return `${API_BASE}/${kind}/${encodeURIComponent(sessionId)}?v=${Date.now()}`;
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
    const text = await res.text();
    throw new Error(text || `Generate failed with status ${res.status}`);
  }

  return res.json();
}

async function requestUpdateParams(payload: UpdateParamsRequest): Promise<UpdateParamsResponse> {
  const res = await fetch(`${API_BASE}/update_params`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Update params failed with status ${res.status}`);
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
    (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)
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
      // Ignore non-JSON messages from the backend.
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
  modelParams: {},
  modelUrl: null,
  stlUrl: null,
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

  setModelParams: (params) => set({ modelParams: params }),

  updateParam: (key, value) =>
    set((state) => ({
      modelParams: { ...state.modelParams, [key]: value },
    })),

  applyGenerateResult: (res) =>
    set((state) => {
      const params = extractModelParams(res);
      return {
        isLoading: false,
        sessionId: res.session_id,
        routeDecision: res.route_decision,
        generatedScriptPath: res.generated_script_path,
        tracePath: res.trace_path,
        consolidatedPrompt: res.consolidated_prompt,
        refinedDesignBrief: res.refined_design_brief,
        currentNode: "生成完成",
        modelUrl: buildAssetUrl("glb", res.session_id, res.glb_path),
        stlUrl: buildAssetUrl("stl", res.session_id, res.stl_path),
        modelParams: Object.keys(params).length > 0 ? params : state.modelParams,
        logs: [...state.logs, ...res.execution_log.filter(Boolean)],
        errors: [...state.errors, ...res.errors.filter(Boolean)],
      };
    }),

  applyUpdateParamsResult: (res, patch = {}) =>
    set((state) => {
      const nextSessionId = res.session_id ?? state.sessionId;
      const paramsFromResponse = extractModelParams(res);
      const nextParams =
        Object.keys(paramsFromResponse).length > 0
          ? paramsFromResponse
          : { ...state.modelParams, ...patch };

      return {
        modelParams: nextParams,
        modelUrl: buildAssetUrl("glb", nextSessionId, res.glb_path),
        stlUrl: buildAssetUrl("stl", nextSessionId, res.stl_path),
        currentNode: res.status === "passed" ? "参数更新完成" : "参数更新失败",
      };
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
          modelUrl: event.glb_path ? buildAssetUrl("glb", event.session_id, event.glb_path) : state.modelUrl,
          stlUrl: event.stl_path ? buildAssetUrl("stl", event.session_id, event.stl_path) : state.stlUrl,
        }));
        get().addLog("✔ 生成完成");
        if (event.glb_path) {
          get().addLog(`✔ GLB: ${event.glb_path}`);
        }
        if (event.stl_path) {
          get().addLog(`✔ STL: ${event.stl_path}`);
        }
        break;
      case "generation.error":
        set({ isLoading: false, currentNode: "生成失败" });
        get().addError(event.error);
        break;
      case "update_params.start":
        set({ currentNode: "参数更新中…" });
        get().addLog("▶ 参数更新中…");
        break;
      case "update_params.complete":
        set((state) => ({
          currentNode: "参数更新完成",
          modelUrl: event.glb_path ? buildAssetUrl("glb", event.session_id, event.glb_path) : state.modelUrl,
          stlUrl: event.stl_path ? buildAssetUrl("stl", event.session_id, event.stl_path) : state.stlUrl,
        }));
        get().addLog("✔ 模型已更新");
        if (event.stl_path) {
          get().addLog(`✔ STL: ${event.stl_path}`);
        }
        break;
      case "update_params.error":
        set({ currentNode: "参数更新失败" });
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

    set({
      isLoading: true,
      userInput: trimmedInput,
      sessionId,
      currentNode: "准备生成…",
      logs: [`用户: ${trimmedInput}`],
      errors: [],
    });

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

  runUpdateParams: async (params, overrides = {}) => {
    const sessionId = get().sessionId;
    if (!sessionId) {
      throw new Error("当前没有可更新的会话");
    }

    set((state) => ({
      modelParams: { ...state.modelParams, ...params },
      currentNode: "参数更新中…",
    }));

    get().addLog(
      `参数变更: ${Object.entries(params)
        .map(([key, value]) => `${key}=${String(value)}`)
        .join(", ")}`,
    );

    openSessionSocket(sessionId);

    try {
      const res = await requestUpdateParams({
        session_id: sessionId,
        params,
        ...overrides,
      });
      get().applyUpdateParamsResult(res, params);
      return res;
    } catch (error) {
      const message = formatError(error);
      set({ currentNode: "参数更新失败" });
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
      modelParams: {},
      modelUrl: null,
      stlUrl: null,
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
      wsConnected: false,
    });
  },
}));
