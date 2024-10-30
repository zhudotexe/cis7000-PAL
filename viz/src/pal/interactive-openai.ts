import { API, WS_BASE } from "@/redel/api";
import type { BaseEvent, ChatMessage, RootMessage, AudioDelta, SendMessage, SendAudio } from "@/pal/models";
import type { RealtimeEvent } from "@/pal/models";
import { AudioQueueManager } from "@/pal/audio";
import { ChatRole } from "@/pal/models";
import { ReDelState } from "@/redel/state";
import { RealtimeClient } from '@openai/realtime-api-beta';

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
  client: RealtimeClient;
  audioQueueManager: AudioQueueManager;
  currentClientTranscript: string = '';
  currentServerTranscript: string = '';

  // events
  events = new EventTarget();
  isReady: boolean = false;

  public constructor(sessionId: string, startState?: ReDelState) {
    this.sessionId = sessionId;
    if (startState) {
      this.state = startState;
    } else {
      this.state = new ReDelState();
    }
    // openai-browser
    const apiKey = "API_KEY_HERE";
    this.client = new RealtimeClient({
      apiKey: apiKey,
      dangerouslyAllowAPIKeyInBrowser: true,
    });
    this.client.updateSession({
      turn_detection: { type: 'server_vad' },
      input_audio_transcription: { model: 'whisper-1' },
      voice: 'alloy',
      instructions: 'I want you to tutor me, a medical student, on how to have a good conversation with a patient and then role play with me. You are the patient, Sarah, and I am the doctor. You should speak like a sick patient. Your voice should sound pretty emotional at times. You should also speak slightly faster than normal.',
    });
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
    // openai-browser
    try {
      this.client.connect().then(() => {
        // Set up event handlers
        this.client.on('realtime.event', (event: any) => this.handleRealtimeEvent(event));
        // Mark as ready
        this.isReady = true;
        this.events.dispatchEvent(new Event("_ready"));
      });
    } catch (error) {
      console.error("Failed to connect:", error);
    }
  }

  public close() {
    this.ws?.close(1000);
    // openai-browser
    this.client.disconnect();
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
    const uint8Array = new Uint8Array(audioData.buffer);
    let binaryString = '';
    for (let i = 0; i < uint8Array.length; i++) {
      binaryString += String.fromCharCode(uint8Array[i]);
    }

    const payload: SendAudio = { type: "send_audio", audio: btoa(binaryString) };
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
    if (message.type === "audio_delta") {
      let delta = atob((message as AudioDelta).delta)
      const audioDelta8 = new Uint8Array(delta.length);
      for (let i = 0; i < delta.length; i++) {
        audioDelta8[i] = delta.charCodeAt(i);
      }
      this.audioQueueManager.addAudioToQueue(new Int16Array(audioDelta8));
    } else {
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

  // ==== openai-browser event handlers ====
  private handleRealtimeEvent({ source, event } : RealtimeEvent) {
    if (source !== 'server') return; 

    switch (event.type) {
      case 'response.audio.delta':
        const audioData = this.base64ToInt16Array(event.delta);
        this.audioQueueManager.addAudioToQueue(audioData);
        // this.handleAudioDelta(event);
        break;
      case 'conversation.item.input_audio_transcription.completed':
        const clientMessage: ChatMessage = {
          role: ChatRole.user,
          content: event.transcript,
          name: "Doctor",
          tool_call_id: null,
          tool_calls: []
        };
        this.state.rootKani?.chat_history.push(clientMessage);
        console.log('Client:', event.transcript);
        break
      case 'response.audio_transcript.delta':
        this.currentServerTranscript += event.delta;
        break;
      case 'response.audio_transcript.done':
        const serverMessage: ChatMessage = {
          role: ChatRole.system,
          content: this.currentServerTranscript,
          name: "Patient",
          tool_call_id: null,
          tool_calls: []
        };
        setTimeout(() => {
          this.state.rootKani?.chat_history.push(serverMessage);
        }, 1000);
        console.log('Server:', this.currentServerTranscript);

        this.currentServerTranscript = "";
        break;
      default:
        // Ignore other events
        break;
    }
  }
  
  private base64ToInt16Array(base64: string): Int16Array {
    const binaryString = atob(base64);
    const len = binaryString.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    return new Int16Array(bytes.buffer);
  }  private audioContext: AudioContext = new AudioContext();

  private processAudioData(audioData: Int16Array): void {
    const audioBuffer = this.audioContext.createBuffer(1, audioData.length, 16000);
    const channelData = audioBuffer.getChannelData(0);
  
    // Convert Int16Array to Float32Array (normalized between -1 and 1)
    for (let i = 0; i < audioData.length; i++) {
      channelData[i] = audioData[i] / 32768; // Int16 max value
    }
  
    const source = this.audioContext.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(this.audioContext.destination);
    source.start();
  }
}
