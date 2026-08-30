import fs from 'node:fs/promises'
import { Presentation, PresentationFile } from '@oai/artifact-tool'

const ROOT = '/Users/adilhusain/Downloads/Synchus'
const OUT = `${ROOT}/presentation`
const ASSET = `${OUT}/assets`
const RENDER = `${OUT}/rendered`
const W = 1920
const H = 1080
const imageBytes = {}

const C = {
  ink: '#17201c',
  cream: '#f6f1e7',
  paper: '#fffaf0',
  moss: '#4d653c',
  lime: '#c8ff3d',
  coral: '#f07252',
  sky: '#dceefa',
  lavender: '#e8e0f4',
  yellow: '#fff0ae',
  muted: '#65706a',
  line: '#d7d0c1',
  deep: '#101a16',
}

async function writeBlob(path, blob) {
  await fs.writeFile(path, new Uint8Array(await blob.arrayBuffer()))
}

function rect(slide, x, y, w, h, fill, radius = 0, line = 'none') {
  return slide.shapes.add({
    geometry: radius ? 'roundRect' : 'rect',
    position: { left: x, top: y, width: w, height: h },
    fill,
    line: { style: 'solid', fill: line, width: line === 'none' ? 0 : 1 },
    ...(radius ? { borderRadius: `rounded-${radius === 999 ? 'full' : '2xl'}` } : {}),
  })
}

function text(slide, value, x, y, w, h, opts = {}) {
  const shape = slide.shapes.add({
    geometry: 'textbox',
    position: { left: x, top: y, width: w, height: h },
    fill: 'none',
    line: { style: 'solid', fill: 'none', width: 0 },
  })
  shape.text = value
  shape.text.style = {
    fontFace: opts.fontFace || 'Aptos',
    fontSize: opts.fontSize || 24,
    color: opts.color || C.ink,
    bold: opts.bold || false,
    italic: opts.italic || false,
    align: opts.align || 'left',
  }
  return shape
}

function eyebrow(slide, value, x, y, w, color = C.moss) {
  return text(slide, value.toUpperCase(), x, y, w, 28, { fontFace: 'Aptos Mono', fontSize: 14, bold: true, color })
}

function rule(slide, x, y, w, color = C.line) {
  return rect(slide, x, y, w, 2, color)
}

function pill(slide, value, x, y, w, fill = C.lime, color = C.ink) {
  rect(slide, x, y, w, 36, fill, 999)
  text(slide, value.toUpperCase(), x + 14, y + 8, w - 28, 18, { fontFace: 'Aptos Mono', fontSize: 12, bold: true, color, align: 'center' })
}

function numberCard(slide, num, label, x, y, fill) {
  rect(slide, x, y, 318, 180, fill, 18, C.line)
  text(slide, num, x + 24, y + 33, 110, 72, { fontSize: 56, bold: true })
  text(slide, label, x + 24, y + 117, 265, 36, { fontFace: 'Aptos Mono', fontSize: 13, bold: true, color: C.muted })
  rect(slide, x + 278, y + 25, 12, 12, C.ink, 999)
}

function addImage(slide, name, x, y, w, h, options = {}) {
  return slide.images.add({
    blob: imageBytes[name],
    contentType: 'image/png',
    alt: options.alt || name,
    fit: options.fit || 'cover',
    position: { left: x, top: y, width: w, height: h },
    geometry: 'roundRect',
    borderRadius: 'rounded-2xl',
    ...(options.crop ? { crop: options.crop } : {}),
  })
}

function note(slide, narration, sources) {
  slide.speakerNotes.textFrame.setText(`${narration}\n\n[Sources]\n${sources}`)
  slide.speakerNotes.setVisible(true)
}

function addFooter(slide, n) {
  text(slide, 'SYNCHUS', 96, 1016, 160, 24, { fontFace: 'Aptos Mono', fontSize: 12, bold: true, color: C.moss })
  text(slide, String(n).padStart(2, '0'), 1736, 1016, 88, 24, { fontFace: 'Aptos Mono', fontSize: 12, bold: true, color: C.moss, align: 'right' })
}

function titleSlide(presentation) {
  const slide = presentation.slides.add()
  slide.background.fill = C.cream
  addImage(slide, 'synchus-hero.png', 830, 42, 1000, 950, { alt: 'Synchus operational memory illustration', fit: 'cover', crop: { left: 0.20, top: 0, right: 0, bottom: 0 } })
  rect(slide, 84, 92, 150, 52, C.ink, 18)
  text(slide, 'SYNCHUS', 102, 106, 114, 24, { fontFace: 'Aptos Mono', fontSize: 15, bold: true, color: C.paper, align: 'center' })
  eyebrow(slide, 'Operational memory for Indian logistics', 92, 238, 660)
  text(slide, 'The company learns at the speed of its ground truth.', 88, 286, 715, 260, { fontSize: 70, bold: true })
  text(slide, 'Voice, files, field reports and operational systems become one living context layer — with humans retaining authority.', 92, 590, 630, 120, { fontSize: 27, color: C.muted })
  pill(slide, 'Hackathon demo', 92, 778, 180, C.lime)
  text(slide, 'Hindi · Hinglish · English', 92, 854, 330, 34, { fontSize: 18, bold: true, color: C.moss })
  text(slide, '2026', 92, 980, 200, 28, { fontFace: 'Aptos Mono', fontSize: 14, color: C.muted })
  note(slide, 'Open with the idea, not the software. Synchus is not another dashboard. It is a way for the company to remember what the people closest to the work already know.', 'Hero illustration: original asset generated with OpenAI image generation for this deck. Product concept and copy: Synchus project team.')
}

function problemSlide(presentation) {
  const slide = presentation.slides.add()
  slide.background.fill = C.paper
  eyebrow(slide, 'The real operational problem', 96, 84, 420, C.coral)
  text(slide, 'The system of record is never the whole truth.', 96, 130, 1110, 90, { fontSize: 54, bold: true })
  text(slide, 'Every company has documents, dashboards and people who know what changed ten minutes ago. Those truths rarely meet.', 98, 236, 940, 72, { fontSize: 25, color: C.muted })
  const cards = [
    ['Files & sheets', 'Contracts, logs, tickets\nand scattered exports', C.sky],
    ['Operational systems', 'Fleet, routes, hubs\nand service records', C.lavender],
    ['Ground reality', 'Voice notes, calls\nand worker observations', '#f8dfd4'],
  ]
  cards.forEach(([heading, body, fill], i) => {
    const x = 96 + i * 450
    rect(slide, x, 390, 366, 258, fill, 18, C.line)
    rect(slide, x + 28, 420, 44, 44, C.ink, 999)
    text(slide, String(i + 1), x + 28, 431, 44, 20, { fontFace: 'Aptos Mono', fontSize: 14, bold: true, color: C.paper, align: 'center' })
    text(slide, heading, x + 28, 490, 306, 38, { fontSize: 27, bold: true })
    text(slide, body, x + 28, 545, 292, 62, { fontSize: 19, color: C.muted })
  })
  rect(slide, 96, 750, 1380, 126, C.ink, 18)
  text(slide, 'The consequence: decisions are made from partial context, while the people who could complete the picture have no structured way to contribute.', 132, 781, 1300, 72, { fontSize: 26, bold: true, color: C.paper })
  addFooter(slide, 2)
  note(slide, 'This is the tension we designed for. Not a lack of data. A lack of shared, trusted context between files, systems and the field.', 'Product framing and copy: Synchus project team. No external statistics used.')
}

function contextSlide(presentation) {
  const slide = presentation.slides.add()
  slide.background.fill = C.cream
  eyebrow(slide, 'The Synchus context layer', 96, 84, 420)
  text(slide, 'One living operational memory.', 96, 128, 940, 76, { fontSize: 54, bold: true })
  text(slide, 'Synchus keeps raw inputs, reasons across connected evidence, separates known from unknown, and stages only useful changes for human approval.', 98, 232, 1040, 64, { fontSize: 24, color: C.muted })
  const flow = [
    ['Listen', 'Voice, Telegram, uploads\nand existing systems', C.sky],
    ['Reconcile', 'Match entities, conflicts,\nlocations and time', C.lavender],
    ['Reason', 'Find what matters,\nwhat is missing and why', '#e8f1dc'],
    ['Act safely', 'Answer, stage, approve,\naudit and reverse', C.yellow],
  ]
  flow.forEach(([title, body, fill], i) => {
    const x = 96 + i * 430
    rect(slide, x, 420, 334, 292, fill, 20, C.line)
    text(slide, `0${i + 1}`, x + 28, 450, 70, 30, { fontFace: 'Aptos Mono', fontSize: 16, bold: true, color: C.moss })
    text(slide, title, x + 28, 505, 260, 42, { fontSize: 30, bold: true })
    text(slide, body, x + 28, 570, 260, 70, { fontSize: 19, color: C.muted })
    if (i < 3) text(slide, '→', x + 350, 530, 40, 40, { fontSize: 30, bold: true, color: C.coral, align: 'center' })
  })
  pill(slide, 'Human approval is the boundary', 96, 804, 320, C.lime)
  text(slide, 'Raw events remain preserved. Canonical context changes only after a person approves it.', 438, 810, 850, 32, { fontSize: 20, bold: true, color: C.moss })
  addFooter(slide, 3)
  note(slide, 'Walk through the loop: Listen, reconcile, reason, act safely. The important bit is that Synchus never turns an uncertain field report into permanent truth by itself.', 'System design: Synchus project team.')
}

function routeSlide(presentation) {
  const slide = presentation.slides.add()
  slide.background.fill = C.paper
  eyebrow(slide, 'Spatial intelligence', 96, 76, 360, C.coral)
  text(slide, 'A route becomes a decision — with evidence.', 96, 116, 1080, 118, { fontSize: 44, bold: true })
  text(slide, 'Select a route and see its hubs, assigned fleet, route precautions, historical patterns and honest gaps in live data.', 98, 250, 1020, 60, { fontSize: 23, color: C.muted })
  addImage(slide, 'synchus-route.png', 96, 330, 1130, 610, { alt: 'Synchus route intelligence dashboard', crop: { left: 0, top: 0, right: 0, bottom: 0 } })
  rect(slide, 1288, 330, 530, 610, '#e9f0df', 20, C.line)
  text(slide, 'What the map makes visible', 1332, 380, 400, 38, { fontSize: 27, bold: true })
  const points = ['Route geometry and distance', 'Hub clusters and home assignments', 'Precautions and historical incidents', 'What is missing — without pretending it is live']
  points.forEach((point, i) => {
    rect(slide, 1334, 462 + i * 92, 26, 26, i === 3 ? C.coral : C.lime, 999)
    text(slide, point, 1380, 457 + i * 92, 365, 50, { fontSize: 19, bold: i === 3, color: i === 3 ? '#8a3e2a' : C.ink })
  })
  pill(slide, 'Not a live GPS claim', 1334, 810, 242, C.yellow)
  text(slide, 'The app distinguishes static evidence from live feeds — visibly.', 1334, 862, 390, 48, { fontSize: 17, bold: true, color: C.moss })
  addFooter(slide, 4)
  note(slide, 'This is not a live-tracking theatre. It is an evidence map. Hubs and fleet assignments are clear. It also plainly says when current positions or yard counts are not connected.', 'Product screenshot: locally captured from Synchus route intelligence. Basemap: OpenStreetMap contributors. Route geometry: OSRM road route.')
}

function voiceSlide(presentation) {
  const slide = presentation.slides.add()
  slide.background.fill = C.deep
  eyebrow(slide, 'Ground truth, in the worker’s language', 96, 80, 600, C.lime)
  text(slide, 'The worker does not fill a form. Synchus conducts the interview.', 96, 122, 980, 142, { fontSize: 52, bold: true, color: C.paper })
  text(slide, 'Hindi, Hinglish or English — voice is the fastest way to get the detail the company is missing.', 98, 292, 900, 58, { fontSize: 23, color: '#c7d1ca' })
  addImage(slide, 'synchus-live.png', 1110, 68, 700, 852, { alt: 'Synchus voice orb interface', fit: 'cover' })
  const dialogue = [
    ['Worker', '“NH44 par blockage hai.”', '#e8e0f4'],
    ['Synchus', '“Kis vehicle, exact location, severity aur expected end time?”', '#e7f2d8'],
    ['Worker', '“DL30AN8381, Murthal, medium, 18:30 tak clear ho sakta hai.”', '#e8e0f4'],
    ['Synchus', '“Confirm karun? Is report ko review ke liye stage kar raha hoon.”', '#fff0ae'],
  ]
  dialogue.forEach(([speaker, line, fill], i) => {
    const y = 425 + i * 126
    rect(slide, 96, y, 900, 102, fill, 18)
    text(slide, speaker, 122, y + 18, 126, 24, { fontFace: 'Aptos Mono', fontSize: 13, bold: true, color: C.moss })
    text(slide, line, 122, y + 48, 820, 34, { fontSize: 20, bold: true })
  })
  text(slide, 'Press Space to begin. Press Space again to stop.', 96, 956, 620, 28, { fontFace: 'Aptos Mono', fontSize: 15, bold: true, color: C.lime })
  addFooter(slide, 5)
  note(slide, 'Use this as the live moment. Speak the first worker line. The agent should ask for the minimum information it needs before it stages a report. That turns voice into reliable operational input instead of an unstructured note.', 'Product screenshot: locally captured Synchus Live interface. Voice intake policy and conversation examples: Synchus project team.')
}

function capabilitySlide(presentation) {
  const slide = presentation.slides.add()
  slide.background.fill = C.cream
  eyebrow(slide, 'Capability lab', 96, 84, 280, C.coral)
  text(slide, 'When the model is missing, Synchus proposes the smallest safe extension.', 96, 126, 1450, 110, { fontSize: 50, bold: true })
  text(slide, 'Some useful information does not fit today’s tables. Synchus can turn that gap into a reviewable capability proposal — never an unreviewed database mutation.', 98, 266, 1280, 62, { fontSize: 23, color: C.muted })
  rect(slide, 96, 410, 484, 410, '#f8dfd4', 20, C.line)
  eyebrow(slide, 'Incoming evidence', 130, 446, 260, '#a84b38')
  text(slide, 'Cold-chain readings arrive in a CSV.', 130, 496, 360, 70, { fontSize: 28, bold: true })
  text(slide, '“Temperature excursions must be linked to a vehicle, shipment and time window.”', 130, 596, 360, 88, { fontSize: 20, color: C.muted })
  pill(slide, 'No current entity exists', 130, 730, 260, C.yellow, '#82520d')
  text(slide, '→', 624, 556, 100, 64, { fontSize: 50, bold: true, color: C.coral, align: 'center' })
  rect(slide, 748, 386, 560, 466, C.lavender, 20, C.line)
  eyebrow(slide, 'Agent proposal', 786, 424, 260, '#62538a')
  text(slide, 'cold_chain_reading', 786, 470, 350, 48, { fontFace: 'Aptos Mono', fontSize: 28, bold: true })
  ;['vehicle_registration · text · required', 'recorded_at · timestamp · required', 'temperature_c · number · required', 'shipment_ref · text · optional'].forEach((row, i) => {
    rect(slide, 786, 546 + i * 58, 450, 42, '#f8f6fc', 12)
    text(slide, row, 804, 558 + i * 58, 410, 20, { fontFace: 'Aptos Mono', fontSize: 13, bold: true, color: '#534f63' })
  })
  text(slide, '→', 1350, 556, 100, 64, { fontSize: 50, bold: true, color: C.coral, align: 'center' })
  rect(slide, 1466, 410, 350, 410, '#e9f0df', 20, C.line)
  eyebrow(slide, 'Human review', 1502, 446, 250, C.moss)
  text(slide, 'Approve\nor reject.', 1502, 502, 260, 82, { fontSize: 32, bold: true })
  text(slide, 'Approval creates the capability. Rejection preserves the raw evidence and the audit trail.', 1502, 630, 260, 106, { fontSize: 18, color: C.muted })
  pill(slide, 'Reversible', 1502, 758, 150, C.lime)
  addFooter(slide, 6)
  note(slide, 'This is an important differentiator. When a document describes a new kind of operational fact, the system can propose a bounded schema and its required checks. People approve it. Every extension is reversible and auditable.', 'Capability Lab design and example: Synchus project team. Demo data: demo/02_cold_chain_readings.csv.')
}

function trustSlide(presentation) {
  const slide = presentation.slides.add()
  slide.background.fill = C.paper
  eyebrow(slide, 'Trust is a product surface', 96, 76, 390, C.coral)
  text(slide, 'Useful intelligence, without a black box.', 96, 116, 1100, 70, { fontSize: 50, bold: true })
  text(slide, 'Synchus keeps the source, the reasoning, the uncertainty and the human decision visible together.', 98, 204, 1080, 56, { fontSize: 23, color: C.muted })
  addImage(slide, 'synchus-approvals.png', 96, 334, 850, 520, { alt: 'Synchus approval queue' })
  addImage(slide, 'synchus-audit.png', 988, 334, 830, 520, { alt: 'Synchus audit ledger' })
  const tags = [
    ['Evidence stays linked', C.sky],
    ['Unknowns stay visible', C.yellow],
    ['Approvals preserve authority', '#e9f0df'],
    ['Changes can be reversed', C.lavender],
  ]
  tags.forEach(([label, fill], i) => {
    const x = 96 + i * 430
    rect(slide, x, 906, 386, 62, fill, 18, C.line)
    text(slide, label, x + 20, 925, 346, 24, { fontSize: 17, bold: true, align: 'center' })
  })
  addFooter(slide, 7)
  note(slide, 'Show the approval queue and audit ledger together. The answer is not the product. The evidence behind the answer, its uncertainty and the ability to reverse a decision are the product.', 'Product screenshots: locally captured Synchus approval queue and audit ledger.')
}

function closeSlide(presentation) {
  const slide = presentation.slides.add()
  slide.background.fill = C.ink
  rect(slide, 0, 0, W, 16, C.lime)
  eyebrow(slide, 'The Synchus promise', 96, 102, 400, C.lime)
  text(slide, 'Files become evidence.\nVoices become structured knowledge.\nMaps become decisions.', 96, 158, 1180, 270, { fontSize: 58, bold: true, color: C.paper })
  text(slide, 'And through it all, the company keeps its human judgment.', 98, 474, 880, 45, { fontSize: 25, color: '#c7d1ca' })
  rect(slide, 96, 620, 1612, 2, '#3d4c44')
  const end = [
    ['Listen to the field', 'Speak in Hindi, Hinglish or English.'],
    ['See the operation', 'Routes, hubs, fleet and evidence in context.'],
    ['Learn safely', 'Propose, approve, audit and reverse.'],
  ]
  end.forEach(([heading, body], i) => {
    const x = 96 + i * 540
    text(slide, `0${i + 1}`, x, 684, 56, 30, { fontFace: 'Aptos Mono', fontSize: 16, bold: true, color: C.lime })
    text(slide, heading, x, 738, 420, 42, { fontSize: 28, bold: true, color: C.paper })
    text(slide, body, x, 800, 400, 40, { fontSize: 19, color: '#c7d1ca' })
  })
  pill(slide, 'The company learns at the speed of its ground truth', 96, 934, 600, C.lime)
  text(slide, 'SYNCHUS', 1530, 970, 280, 34, { fontFace: 'Aptos Mono', fontSize: 18, bold: true, color: C.lime, align: 'right' })
  note(slide, 'Close exactly here: “Synchus is not asking the company to become more technical. It is helping the company listen to itself — safely, in the language its people already use.” Then pause.', 'Closing copy: Synchus project team.')
}

async function main() {
  await fs.mkdir(RENDER, { recursive: true })
  for (const name of ['synchus-hero.png', 'synchus-route.png', 'synchus-live.png', 'synchus-approvals.png', 'synchus-audit.png']) {
    imageBytes[name] = await fs.readFile(`${ASSET}/${name}`)
  }
  const presentation = Presentation.create({ slideSize: { width: W, height: H } })
  titleSlide(presentation)
  problemSlide(presentation)
  contextSlide(presentation)
  routeSlide(presentation)
  voiceSlide(presentation)
  capabilitySlide(presentation)
  trustSlide(presentation)
  closeSlide(presentation)

  for (const [i, slide] of presentation.slides.items.entries()) {
    const stem = `slide-${String(i + 1).padStart(2, '0')}`
    await writeBlob(`${RENDER}/${stem}.png`, await presentation.export({ slide, format: 'png', scale: 1 }))
    await fs.writeFile(`${RENDER}/${stem}.layout.json`, await (await slide.export({ format: 'layout' })).text())
  }
  await writeBlob(`${RENDER}/deck-montage.webp`, await presentation.export({ format: 'webp', montage: true, scale: 1 }))
  const pptx = await PresentationFile.exportPptx(presentation)
  await pptx.save(`${OUT}/Synchus_Operational_Memory.pptx`)
}

main().catch((error) => { console.error(error); process.exitCode = 1 })
