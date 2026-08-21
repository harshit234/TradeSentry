const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
export type DocumentItem = { document_id:string; case_id:string; filename:string; document_type:string; status:string; overall_confidence:number|null; extraction_flags:string[]; view_url:string|null; extraction:{fields:unknown;page_refs:Record<string,number[]>}|null; error_code:string|null; advisory:string|null };
export type Completeness = { required_types:string[]; present_types:string[]; missing_types:string[]; status:"COMPLETE"|"INCOMPLETE"|"PENDING_LC"; can_run_investigation:boolean };
async function json<T>(response:Response):Promise<T>{if(!response.ok){const body=(await response.json().catch(()=>({}))) as {detail?:string};throw new Error(body.detail??`Request failed: ${response.status}`)}return response.json() as Promise<T>}
export async function createCase(caseId:string,ibuId:string){return json(await fetch(`${API_URL}/cases`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({case_id:caseId,ibu_id:ibuId})}))}
export async function uploadDocument(caseId:string,file:File){const body=new FormData();body.append("file",file);return json<{document_id:string;status:string}>(await fetch(`${API_URL}/cases/${caseId}/documents`,{method:"POST",body}))}
export async function getDocuments(caseId:string):Promise<DocumentItem[]>{return json(await fetch(`${API_URL}/cases/${caseId}/documents`,{cache:"no-store"}))}
export async function getDocument(caseId:string,documentId:string):Promise<DocumentItem>{return json(await fetch(`${API_URL}/cases/${caseId}/documents/${documentId}`,{cache:"no-store"}))}
export async function getCompleteness(caseId:string):Promise<Completeness>{return json(await fetch(`${API_URL}/cases/${caseId}/completeness`,{cache:"no-store"}))}
