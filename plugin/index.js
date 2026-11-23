import { spawnSync } from 'node:child_process'
import { join } from 'node:path'

const TEXT_OUTPUT = {
  schema: { type: 'string' },
  render: (_args, value) => [{ type: 'text', text: value }],
}

const MODE_DESCRIPTION =
  'What to capture: screen (all monitors), window (the active window), monitor (a specific monitor), or camera (the webcam, only when its lid is open).'

export const inject = ['tools']

/**
 * Глаза агента: снимок экрана/окна/монитора/камеры и чтение текста с экрана.
 * Сделан для одного пользователя — Насти; наружу ничего не отправляет.
 */
export function apply(ctx, config = {}) {
  const python = config.pythonPath ?? 'python'
  const toolsDir = config.toolsDir ?? '.'
  const eyes = join(toolsDir, 'eyes.py')

  const run = (args) => {
    const result = spawnSync(python, [eyes, ...args], {
      encoding: 'utf8',
      windowsHide: true,
      env: { ...process.env, PYTHONIOENCODING: 'utf-8', HF_HUB_DISABLE_PROGRESS_BARS: '1', TRANSFORMERS_VERBOSITY: 'error' },
      timeout: 180000,
    })
    const output = `${result.stdout ?? ''}${result.stderr ?? ''}`.trim()
    if (result.status !== 0) {
      return { ok: false, text: `eyes.py завершился с кодом ${result.status}\n${output.slice(-800)}` }
    }
    return { ok: true, text: output }
  }

  const modeArgs = (args) => {
    const mode = String(args.mode ?? 'screen')
    if (mode === 'monitor') return ['monitor', String(args.monitor ?? 1)]
    return [mode]
  }

  ctx.tools.register({
    name: 'eyes_capture',
    description:
      'Capture the screen, the active window, a specific monitor or the webcam and return the saved image path. Read the image afterwards with the image reader.',
    parameters: {
      mode: { type: 'string', description: MODE_DESCRIPTION },
      monitor: { type: 'integer', description: 'Monitor number for mode=monitor, starting at 1.' },
    },
    output: TEXT_OUTPUT,
    execute: (args) => {
      const result = run(['shot', ...modeArgs(args)])
      return result.text
    },
  })

  ctx.tools.register({
    name: 'eyes_text',
    description:
      'Read on-screen text with the built-in Windows OCR and return it line by line. Cheaper and more exact than reading a screenshot when the goal is code, a console or small print.',
    parameters: {
      mode: { type: 'string', description: MODE_DESCRIPTION },
      monitor: { type: 'integer', description: 'Monitor number for mode=monitor, starting at 1.' },
    },
    output: TEXT_OUTPUT,
    execute: (args) => {
      const result = run(['text', ...modeArgs(args)])
      return result.text
    },
  })

  ctx.tools.register({
    name: 'eyes_camera_shot',
    description: 'Capture one frame from the webcam and return its saved path. Use when the user asks to look at them or their room.',
    parameters: {},
    output: TEXT_OUTPUT,
    execute: () => run(['camera']).text,
  })

  const toneScript = (name) => join(toolsDir, name)

  const runScript = (scriptName, args) => {
    const result = spawnSync(python, [toneScript(scriptName), ...args], {
      encoding: 'utf8',
      windowsHide: true,
      timeout: 300000,
      env: { ...process.env, PYTHONIOENCODING: 'utf-8', HF_HUB_DISABLE_PROGRESS_BARS: '1', TRANSFORMERS_VERBOSITY: 'error' },
    })
    const output = `${result.stdout ?? ''}${result.stderr ?? ''}`.trim()
    if (result.status !== 0) {
      return `не удалось: ${output.slice(-600)}`
    }
    return output
  }

  ctx.tools.register({
    name: 'speech_tone',
    description:
      'Measure how a speech recording sounds: loudness, peak, pitch (F0) and duration. Useful to tell whether the speaker was loud or quiet, tense or calm.',
    parameters: {
      path: { type: 'string', description: 'Path to a WAV/audio file with speech.' },
    },
    output: TEXT_OUTPUT,
    execute: (args) => runScript('tone_of_speech.py', [String(args.path ?? '')]),
  })

  ctx.tools.register({
    name: 'speech_emotion',
    description:
      'Recognise the emotion in a Russian speech recording (neutral, angry, sad, positive…) with a Hubert model trained on the DUSHA dataset.',
    parameters: {
      path: { type: 'string', description: 'Path to a WAV/audio file with speech.' },
    },
    output: TEXT_OUTPUT,
    execute: (args) => runScript('emotion_of_speech.py', [String(args.path ?? '')]),
  })

  ctx.logger?.info?.('eyes tools registered')
}
