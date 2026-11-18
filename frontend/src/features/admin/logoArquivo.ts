// Mesmos limites da API e do banco (migração 25).
export const TIPOS_DE_LOGO = ['image/png', 'image/jpeg', 'image/webp'];
export const TAMANHO_MAXIMO_LOGO = 512 * 1024;

/** Validação local só para avisar cedo; quem decide é a API, pelos bytes do arquivo. */
export function problemaDoArquivo(arquivo: Pick<File, 'type' | 'size'>): string | null {
    if (!TIPOS_DE_LOGO.includes(arquivo.type)) return 'Use uma imagem PNG, JPEG ou WebP. SVG não é aceito.';
    if (arquivo.size > TAMANHO_MAXIMO_LOGO) return 'A logo deve ter até 512 KB.';
    if (arquivo.size === 0) return 'O arquivo está vazio.';
    return null;
}
