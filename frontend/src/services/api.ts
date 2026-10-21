const base = 'http://127.0.0.1:8765/api/v1'

export type Capture = { id:number; captured_at:string; process_name:string; window_title:string; ocr_text:string }
export type OCRBlock = { text:string; bbox:[number,number,number,number] }
export type CaptureDetails = Capture & { ocr_blocks:OCRBlock[] }
export type SourceScreenshot = Pick<Capture, 'id'|'captured_at'|'process_name'|'window_title'>
export type Settings = { capture_interval_seconds:number; capture_enabled:boolean; ignored_processes:string[] }

async function request<T>(path:string, init?:RequestInit):Promise<T> {
  const response = await fetch(`${base}${path}`, init)
  if (!response.ok) {
    let detail = `Local service returned ${response.status}`
    try { detail = (await response.json()).detail || detail } catch { /* HTTP body may be empty */ }
    throw new Error(detail)
  }
  return response.json()
}

export const api = {
  status: () => request<{online:boolean;capture_enabled:boolean;local_only:boolean}>('/status'),
  timeline: (dateFrom?:string, dateTo?:string) => {
    const params = new URLSearchParams({limit:'100'})
    if (dateFrom) params.set('date_from',dateFrom)
    if (dateTo) params.set('date_to',dateTo)
    return request<Capture[]>(`/timeline?${params}`)
  },
  activity: (dateFrom:string,dateTo:string,utcOffsetMinutes:number) => request<{hours:number[]}>(`/timeline/activity?${new URLSearchParams({date_from:dateFrom,date_to:dateTo,utc_offset_minutes:String(utcOffsetMinutes)})}`),
  search: (q:string,limit=50,mode:'hybrid'|'semantic'|'text'='hybrid') => request<Capture[]>(`/search?${new URLSearchParams({q,limit:String(limit),mode})}`),
  details: (id:number) => request<CaptureDetails>(`/screenshots/${id}/details`),
  settings: () => request<Settings>('/settings'),
  update: (settings:Partial<Settings>) => request<Settings>('/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(settings)}),
  image: (id:number) => `${base}/screenshots/${id}`,
  models: () => request<{models:string[]}>('/chat/models'),
  async chat(query:string,model:string,onEvent:(event:string,data:unknown)=>void,signal?:AbortSignal) {
    const response = await fetch(`${base}/chat`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query,model}),signal})
    if (!response.ok) {
      let detail = `Chat returned ${response.status}`
      try { detail = (await response.json()).detail || detail } catch { /* HTTP body may be empty */ }
      throw new Error(detail)
    }
    if (!response.body) throw new Error('Streaming is unavailable in this browser')
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    while (true) {
      const {done,value} = await reader.read()
      if (done) break
      buffer += decoder.decode(value,{stream:true})
      buffer = buffer.replace(/\r\n/g,'\n')
      let split:number
      while ((split=buffer.indexOf('\n\n')) !== -1) {
        const packet = buffer.slice(0,split)
        buffer = buffer.slice(split+2)
        const event = packet.match(/^event: (.+)$/m)?.[1]
        const data = packet.match(/^data: (.+)$/m)?.[1]
        if (event && data) onEvent(event,JSON.parse(data))
      }
    }
  }
}
