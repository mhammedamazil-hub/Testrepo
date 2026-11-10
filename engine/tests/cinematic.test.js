import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {FILM} from '../src/offline-cinematic.js';
test('offline film uses native 1080p60 and an integer frame count',()=>{assert.equal(FILM.width,1920);assert.equal(FILM.height,1080);assert.equal(FILM.fps,60);assert.equal(FILM.seconds*FILM.fps,180);});
test('offline exporter is opt-in and cannot silently increase gameplay graphics',()=>{const main=fs.readFileSync(new URL('../src/main.js',import.meta.url),'utf8'),film=fs.readFileSync(new URL('../src/offline-cinematic.js',import.meta.url),'utf8');assert.ok(!main.includes('offline-cinematic'));assert.ok(film.includes('frame/FILM.fps'));assert.ok(film.includes('new T.MeshPhysicalMaterial'));assert.ok(film.includes('textureWidth:1024,textureHeight:1024'));assert.ok(!film.includes('localStorage.setItem'));});
