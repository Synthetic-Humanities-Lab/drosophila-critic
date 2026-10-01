import test from 'node:test';
import assert from 'node:assert/strict';
import {parsePassages} from '../static/passage-windows.js';

test('correspondence retains separate native clocks and permits unmarked recordings', () => {
  assert.deepEqual(parsePassages('', ''), []);
  assert.deepEqual(parsePassages('0,2\n3,5', '1,4\n5,8'), [
    {a:{start:0,end:2},b:{start:1,end:4}}, {a:{start:3,end:5},b:{start:5,end:8}},
  ]);
});
test('invalid or unequal annotations fail before uploading audio', () => {
  for (const [a,b] of [['0,2',''], ['0,2\n1,3','0,2\n3,4'], ['0,Infinity','0,2'], ['0,0.1','0,2'], ['0,121','0,2']]) {
    assert.throws(() => parsePassages(a,b));
  }
});
