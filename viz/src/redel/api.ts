import type { BaseEvent, SaveMeta, SessionState } from "@/redel/models";
import { Notifications } from "@/redel/notifications";
import axios from "axios";
import { randomId } from "@/utils";

export const API_BASE = import.meta.env.VITE_API_BASE;
export const WS_BASE = import.meta.env.VITE_WS_BASE;

// On error, automatically add an error notification to Notifications.
axios.interceptors.request.use(
  // noop on success
  (response) => response,
  function (error) {
    Notifications.error(error.message);
    return Promise.reject(error);
  },
);

axios.interceptors.response.use(
  // noop on success
  (response) => response,
  // send httpError to notifications on error
  function (error) {
    Notifications.httpError(error);
    return Promise.reject(error);
  },
);

/**
 * A simple static class to expose all the ReDel REST endpoints.
 */
export class API {
  ////////// UID //////////
  static _uid: string;
  public static get uid(): string {
    if (!this._uid) {
      const lsUid = localStorage.getItem("pal-user-id")!;
      if (!lsUid) return this.resetUid();
      this._uid = lsUid;
    }
    return this._uid;
  }

  public static set uid(v: string) {
    localStorage.setItem("pal-user-id", v);
    this._uid = v;
  }

  public static resetUid(): string {
    this.uid = randomId();
    return this.uid;
  }

  ////////// SAVES //////////
  public static async listSaves() {
    const response = await axios.get<SaveMeta[]>(`${API_BASE}/saves`);
    return response.data;
  }

  public static async getSaveState(saveId: string) {
    const response = await axios.get<SessionState>(`${API_BASE}/saves/${saveId}`);
    return response.data;
  }

  public static async getSaveEvents(saveId: string) {
    const response = await axios.get<BaseEvent[]>(`${API_BASE}/saves/${saveId}/events`);
    return response.data;
  }

  public static async deleteSave(saveId: string) {
    const response = await axios.delete<SaveMeta>(`${API_BASE}/saves/${saveId}`);
    return response.data;
  }

  ////////// INTERACTIVE //////////
  public static async listStatesInteractive() {
    const config = {
      params: {
        uid: this.uid,
      },
    };
    const response = await axios.get<SessionState[]>(`${API_BASE}/states`, config);
    return response.data;
  }

  public static async createStateInteractive(startContent?: string) {
    const config = {
      params: {
        uid: this.uid,
      },
    };
    const data = startContent ? { start_content: startContent } : undefined;
    const response = await axios.post<SessionState>(`${API_BASE}/states`, data, config);
    return response.data;
  }

  public static async getStateInteractive(sessionId: string) {
    const response = await axios.get<SessionState>(`${API_BASE}/states/${sessionId}`);
    return response.data;
  }

  public static async initPalStates() {
    const config = {
      params: {
        uid: this.uid,
      },
    };
    const response = await axios.post<SessionState[]>(`${API_BASE}/init-pal-states`, null, config);
    return response.data;
  }
}
