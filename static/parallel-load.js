// Bound temporary chunk buffers on phones; do not retain a second copy of the model.
export async function forEachConcurrent(items, visit, concurrency = 2) {
  if (!Number.isInteger(concurrency) || concurrency < 1)
    throw new Error("Invalid download concurrency.");
  let next = 0,
    failure;
  await Promise.all(
    Array.from({ length: Math.min(concurrency, items.length) }, async () => {
      while (!failure && next < items.length) {
        const index = next++;
        try {
          await visit(items[index], index);
        } catch (error) {
          failure = error;
        }
      }
    }),
  );
  if (failure) throw failure;
}
