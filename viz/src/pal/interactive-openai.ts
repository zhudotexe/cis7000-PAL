import { API, WS_BASE } from "@/redel/api";
import type { BaseEvent, ChatMessage, KaniMessage, RootMessage, StreamDelta, AudioDelta, SendMessage, SendAudio, EndSession } from "@/pal/models";
import type { RealtimeEvent } from "@/pal/models";
import { AudioQueueManager } from "@/pal/audio";
import { ChatRole } from "@/pal/models";
import { ReDelState } from "@/redel/state";

/**
 * API client to handle interactive session with the backend.
 */
export class InteractiveClient {
  state: ReDelState;
  sessionId: string;

  // ws
  ws: WebSocket | null = null;
  isWSConnecting = false;
  isWSDisconnected = false;
  // openai-browser
  audioQueueManager: AudioQueueManager;

  // events
  events = new EventTarget();
  isReady: boolean = false;
  isEnded: boolean = false;

  public constructor(sessionId: string, startState?: ReDelState) {
    this.sessionId = sessionId;
    if (startState) {
      this.state = startState;
    } else {
      this.state = new ReDelState();
    }
    // openai-browser
    this.audioQueueManager = new AudioQueueManager();
  }

  // ==== lifecycle ====
  public connect() {
    this.ws?.close(1000);
    this.ws = new WebSocket(`${WS_BASE}/${this.sessionId}`);
    this.isWSConnecting = true;
    this.ws.addEventListener("open", () => this.onWSOpen());
    this.ws.addEventListener("close", (event) => this.onWSClose(event));
    this.ws.addEventListener("error", (event) => console.warn("WebSocket error: ", event));
    this.ws.addEventListener("message", (event) => this.onRawMessage(event.data));
  }

  public close() {
    this.ws?.close(1000);
  }

  // ==== API ====
  public async getState() {
    try {
      const sessionState = await API.getStateInteractive(this.sessionId);
      this.state.loadSessionState(sessionState);
      // notify ready
      this.isReady = true;
      this.events.dispatchEvent(new Event("_ready"));
      console.debug(`Loaded ${this.state.kaniMap.size} kani states.`);
      return { success: true };
    } catch (error) {
      console.error("Failed to get session state:", error);
      return { success: false, error };
    }
  }

  public sendMessage(msg: string) {
    const payload: SendMessage = { type: "send_message", content: msg };
    this.ws?.send(JSON.stringify(payload));
  }

  public appendAudio(audioData: Int16Array) {
    // this.client.appendInputAudio(audioData);

    // Convert Int16Array to Base64
    var bytes = new Uint8Array(audioData.buffer, audioData.byteOffset, audioData.byteLength);
    var binary = '';
    for (var i = 0; i < bytes.byteLength; i++) {
        binary += String.fromCharCode(bytes[i]);
    }

    const payload: SendAudio = { type: "send_audio", audio: btoa(binary) };
    this.ws?.send(JSON.stringify(payload));

    // Uncomment to playback audio
    // this.audioQueueManager.addAudioToQueue(this.base64ToInt16Array(payload.audio));
  }

  public endSession(transcript: string) {
    this.isEnded = true;

    const payload: EndSession = { type: "end_session", transcript: transcript };
    this.ws?.send(JSON.stringify(payload));
  }

  // ==== utils ====
  public async waitForReady() {
    if (this.isReady) return true;
    return new Promise<boolean>((resolve) => {
      this.events.addEventListener("_ready", () => resolve(true));
    });
  }

  public async waitForFullReply() {
    return new Promise<ChatMessage>((resolve) => {
      this.events.addEventListener("root_message", ((e: CustomEvent<RootMessage>) => {
        const msg = e.detail.msg;
        if (msg.role == ChatRole.assistant && msg.tool_calls === null) {
          resolve(msg);
        }
      }) as EventListener);
    });
  }

  // ==== event handlers ====
  onRawMessage(data: string) {
    let message: BaseEvent;
    try {
      message = JSON.parse(data);
      console.debug("RECV", message);
    } catch (e) {
      console.warn(e);
      return;
    }
    console.log(message.type);
    if (message.type === "audio_delta") {
      if (this.isEnded)
        return
      this.audioQueueManager.addAudioToQueue(this.base64ToInt16Array((message as AudioDelta).delta));
    } else {
      if (this.isEnded && ((message.type == "root_message" && (message as RootMessage).msg.role !== ChatRole.assistant) || (message.type == "stream_delta" && (message as StreamDelta).role !== ChatRole.assistant) || (message.type == "kani_message" && (message as RootMessage).msg.role !== ChatRole.assistant))) {
        return
      }
      if (this.isEnded && message.type == "kani_message") {
        (message as KaniMessage).msg.role = ChatRole.system;
      }
      this.state.handleEvent(message);
      this.events.dispatchEvent(new CustomEvent(message.type, { detail: message }));
    }
  }

  onWSOpen() {
    console.log("WS connected");
    this.isWSDisconnected = false;
    this.isWSConnecting = false;
  }

  onWSClose(event: CloseEvent) {
    console.log(`WS closed with ${event.code} (reason=${event.reason}; clean=${event.wasClean})`);
    this.isWSDisconnected = true;
    if (event.wasClean && event.code !== 1012) {
      this.isWSConnecting = false;
    } else if (!this.isWSConnecting) {
      // attempt reconnect with exponential backoff
      this.attemptReconnect(1);
    }
  }

  attemptReconnect(attempt: number, maxAttempts = 5) {
    if (!this.isWSDisconnected) return;
    if (attempt > maxAttempts) {
      this.isWSDisconnected = true;
      this.isWSConnecting = false;
      return;
    }
    console.log(`Attempting to reconnect (try ${attempt} of ${maxAttempts})...`);
    this.connect();
    setTimeout(() => this.attemptReconnect(attempt + 1, maxAttempts), attempt * 1000 + Math.random() * 1000);
  }

  private base64ToInt16Array(base64: string): Int16Array {
    const binaryString = atob(base64);
    const len = binaryString.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    return new Int16Array(bytes.buffer);
  } 
}
