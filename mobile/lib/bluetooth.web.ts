/**
 * mobile/lib/bluetooth.web.ts
 * Stub para web — Bluetooth SPP não está disponível no navegador.
 * Metro resolve este arquivo automaticamente na plataforma web.
 */

import type { NmeaFix } from './nmea'

export async function listarDispositivosPareados(): Promise<any[]> { return [] }
export async function conectar(_address: string): Promise<boolean> { return false }
export async function desconectar(): Promise<void> {}
export function isConectado(): boolean { return false }
export function iniciarLeitura(_onFix: (fix: NmeaFix) => void): void {}
export function pararLeitura(): void {}
