import { createInterface } from 'readline/promises';
import { Writable } from 'stream';

async function promptSecret(question: string): Promise<string> {
  // Mute output so typed characters are not echoed to the terminal
  let muted = false;
  const mutedOut = new Writable({
    write(chunk, _enc, cb) {
      if (!muted) process.stdout.write(chunk);
      cb();
    },
  });
  const rl = createInterface({ input: process.stdin, output: mutedOut, terminal: true });
  process.stdout.write(question);
  muted = true;
  const value = await rl.question('');
  muted = false;
  rl.close();
  process.stdout.write('\n');
  return value;
}

export default async function globalSetup() {
  if (process.env.FA_PASSWORD) return;

  if (!process.stdin.isTTY) {
    throw new Error(
      'FA_PASSWORD is not set. In CI, provide it as an environment variable or secret.',
    );
  }

  process.env.FA_PASSWORD = await promptSecret('FA_PASSWORD: ');
}
