import sharp from 'sharp';
import { readdirSync } from 'fs';
import { join, extname, basename } from 'path';
import { fileURLToPath } from 'url';

const publicDir = join(fileURLToPath(import.meta.url), '../../public');

const files = readdirSync(publicDir).filter((f) => /\.(png|jpg|jpeg)$/i.test(f));

console.log(`Otimizando ${files.length} imagens em ${publicDir}...\n`);

let success = 0;
let skipped = 0;

for (const file of files) {
    const input = join(publicDir, file);
    const ext = extname(file);
    const output = join(publicDir, basename(file, ext) + '.webp');

    try {
        await sharp(input)
            .resize(400, 400, { fit: 'inside', withoutEnlargement: true })
            .webp({ quality: 80 })
            .toFile(output);
        console.log(`✓ ${file} → ${basename(output)}`);
        success++;
    } catch (err) {
        console.error(`✗ ${file}: ${err.message}`);
        skipped++;
    }
}

console.log(`\nConcluído: ${success} convertidas, ${skipped} com erro.`);
