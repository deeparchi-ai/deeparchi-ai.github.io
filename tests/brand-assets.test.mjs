import assert from 'node:assert/strict';
import test from 'node:test';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';

const read = path => readFile(new URL(`../${path}`,import.meta.url));
const pages = await Promise.all(['index.html','developers.html','privacy.html'].map(async path => [path,(await read(path)).toString('utf8')]));

test('all public pages use the supplied official logo, not geometric substitutes', () => {
  for (const [path,html] of pages) {
    const brand = html.match(/<a class="brand"[^>]*>([\s\S]*?)<\/a>/)?.[1];
    assert.ok(brand,path);
    assert.match(brand,/<img class="brand-logo" src="assets\/deeparchi-logo\.png" width="498" height="512" alt="DeepArchi 公司标志">/,path);
    assert.match(html,/<link rel="icon" type="image\/png" sizes="128x128" href="assets\/deeparchi-favicon\.png">/,path);
    assert.doesNotMatch(html,/◇|brand-mark|data:image\/svg\+xml/,path);
    assert.equal((html.match(/class="brand-logo"/g)||[]).length,1,path);
  }
});

test('approved logo and favicon PNGs are intact and retain their export dimensions', async () => {
  // Hashes pin proportional exports of the user-supplied official lockup.
  const approved = [
    ['assets/deeparchi-logo.png',498,512,'21d0b1d6e7c5ffd6a39b20bbd680561c2dfc0bcd808116617212b5cf09c3c09c'],
    ['assets/deeparchi-favicon.png',128,128,'ecc52f19baffa81cc44309de247772767e4a5cd98f3a610194dc0d84af6e788f'],
  ];
  for (const [path,width,height,sha256] of approved) {
    const png = await read(path);
    assert.equal(png.subarray(0,8).toString('hex'),'89504e470d0a1a0a');
    assert.equal(png.readUInt32BE(16),width);
    assert.equal(png.readUInt32BE(20),height);
    assert.equal(createHash('sha256').update(png).digest('hex'),sha256,path);
  }
  const css = (await read('assets/site.css')).toString('utf8');
  assert.match(css,/\.brand-logo\{[^}]*height:88px;[^}]*width:auto;[^}]*object-fit:contain/);
  assert.doesNotMatch(css,/\.brand-mark\b/);
});
