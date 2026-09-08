import { api } from "@/api/client";
import type { Transfer, TransferRecipient } from "@/types";

export function listTransferRecipients(): Promise<TransferRecipient[]> {
  return api.get<TransferRecipient[]>("/api/transfers/recipients");
}

export function sendTransfer(recipientId: string, amount: number, note: string | null): Promise<Transfer> {
  return api.post<Transfer>("/api/transfers", { recipient_id: recipientId, amount, note });
}

export function getMyTransferHistory(): Promise<Transfer[]> {
  return api.get<Transfer[]>("/api/transfers/history");
}
