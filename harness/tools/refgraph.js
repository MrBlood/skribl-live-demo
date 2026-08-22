// v2: cover FunctionDeclarations at ANY depth, attribute each identifier
// reference to its innermost enclosing declaration, and let references
// propagate outward (a nested function's reference is also its parent's).
const fs = require('fs');
let acorn, walk;
try {
  acorn = require('acorn');
  walk = require('acorn-walk');
} catch (e) {
  // A bare traceback here reads as a broken tool rather than a missing
  // dependency, and this is deliberately not vendored: it is a measurement
  // utility, not part of the shipped package or of any suite's requirements.
  console.error('refgraph.js needs acorn. From anywhere outside the repo:\n' +
                '  mkdir -p /tmp/refgraph && cd /tmp/refgraph\n' +
                '  npm i acorn acorn-walk\n' +
                '  NODE_PATH=/tmp/refgraph/node_modules node <repo>/harness/tools/refgraph.js ' +
                '<repo>/skribl/static/app.js\n' +
                'Installing into the repo would put node_modules in the tree hash.');
  process.exit(2);
}

const src = fs.readFileSync(process.argv[2], 'utf8');
const ast = acorn.parse(src, { ecmaVersion: 2022 });

const fns = new Map();
walk.full(ast, (n) => {
  if (n.type === 'FunctionDeclaration' && n.id) fns.set(n.id.name, n);
});

const ranges = [...fns.entries()]
  .map(([name, n]) => ({ name, start: n.start, end: n.end }))
  .sort((a, b) => (b.end - b.start) - (a.end - a.start)); // widest first

function chain(pos) {                    // every enclosing decl, outermost..innermost
  return ranges.filter((r) => pos >= r.start && pos < r.end).map((r) => r.name);
}

const skip = new Set();
walk.full(ast, (node) => {
  if (node.type === 'FunctionDeclaration' && node.id) skip.add(node.id);
  if (node.type === 'MemberExpression' && !node.computed) skip.add(node.property);
  if (node.type === 'Property' && !node.computed) skip.add(node.key);
  if (node.type === 'LabeledStatement') skip.add(node.label);
});

const refs = new Map();
const toplevelRefs = new Set();
walk.full(ast, (node) => {
  if (node.type !== 'Identifier' || skip.has(node)) return;
  if (!fns.has(node.name)) return;
  const owners = chain(node.start).filter((o) => o !== node.name);
  if (owners.length === 0) { toplevelRefs.add(node.name); return; }
  for (const o of owners) {              // propagate outward
    if (!refs.has(o)) refs.set(o, new Set());
    refs.get(o).add(node.name);
  }
});

const MARK = '// ==================== READ-ONLY PLAYER ====================';
const p0 = src.indexOf(MARK);
let p1 = src.indexOf('\n// ---------- Image / Music', p0);
if (p1 < 0) p1 = src.length;

const seeds = new Set();
for (const [name, n] of fns) if (n.start >= p0 && n.end <= p1) seeds.add(name);
walk.full(ast, (node) => {
  if (node.type !== 'Identifier' || skip.has(node)) return;
  if (node.start >= p0 && node.start < p1 && fns.has(node.name)) seeds.add(node.name);
});
// a nested seed drags its enclosing declaration in too
for (const s of [...seeds]) for (const o of chain(fns.get(s).start)) seeds.add(o);

const seen = new Set();
const stack = [...seeds];
while (stack.length) {
  const f = stack.pop();
  if (seen.has(f)) continue;
  seen.add(f);
  for (const o of (refs.get(f) || [])) if (!seen.has(o)) stack.push(o);
}

const bytes = (n) => fns.get(n).end - fns.get(n).start;
const editorOnly = [...fns.keys()].filter((n) => !seen.has(n));
const sum = (a) => a.reduce((t, n) => t + bytes(n), 0);
console.log(JSON.stringify({
  total_functions: fns.size,
  player_reachable: [...seen].sort(),
  editor_only: editorOnly.sort(),
  pinned: [...toplevelRefs].sort(),
  bytes: {
    file: Buffer.byteLength(src),
    player_reachable: sum([...seen]),
    editor_only: sum(editorOnly),
    editor_only_free: sum(editorOnly.filter((n) => !toplevelRefs.has(n))),
  },
  free_list: editorOnly.filter((n) => !toplevelRefs.has(n))
    .sort((a, b) => bytes(b) - bytes(a)).map((n) => [n, bytes(n)]),
}, null, 1));
