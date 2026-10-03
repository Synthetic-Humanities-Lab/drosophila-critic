;; Inference-only matrix product: input-major float32 weights, four outputs/lane.
;; Bias, layer normalization and activation remain explicit in body-policy.js.
(module
  (memory (export "memory") 256)
  (func (export "dense") (param $x i32) (param $w i32) (param $y i32)
        (param $inputs i32) (param $outputs i32)
    (local $j i32) (local $i i32) (local $sum v128)
    (local $scalar f32)
    (block $end
      (loop $columns
        (br_if $end (i32.gt_u (i32.add (local.get $j) (i32.const 4)) (local.get $outputs)))
        (local.set $i (i32.const 0))
        (local.set $sum (v128.const f32x4 0 0 0 0))
        (loop $rows
          (local.set $sum (f32x4.add (local.get $sum)
            (f32x4.mul
              (f32x4.splat (f32.load (i32.add (local.get $x) (i32.shl (local.get $i) (i32.const 2)))))
              (v128.load (i32.add (local.get $w) (i32.shl (i32.add (i32.mul (local.get $i) (local.get $outputs)) (local.get $j)) (i32.const 2)))))))
          (local.set $i (i32.add (local.get $i) (i32.const 1)))
          (br_if $rows (i32.lt_u (local.get $i) (local.get $inputs))))
        (v128.store (i32.add (local.get $y) (i32.shl (local.get $j) (i32.const 2))) (local.get $sum))
        (local.set $j (i32.add (local.get $j) (i32.const 4)))
        (br $columns)))
    (block $done
      (loop $tail
        (br_if $done (i32.ge_u (local.get $j) (local.get $outputs)))
        (local.set $i (i32.const 0))
        (local.set $scalar (f32.const 0))
        (loop $tailrows
          (local.set $scalar (f32.add (local.get $scalar)
            (f32.mul
              (f32.load (i32.add (local.get $x) (i32.shl (local.get $i) (i32.const 2))))
              (f32.load (i32.add (local.get $w) (i32.shl (i32.add (i32.mul (local.get $i) (local.get $outputs)) (local.get $j)) (i32.const 2)))))))
          (local.set $i (i32.add (local.get $i) (i32.const 1)))
          (br_if $tailrows (i32.lt_u (local.get $i) (local.get $inputs))))
        (f32.store (i32.add (local.get $y) (i32.shl (local.get $j) (i32.const 2))) (local.get $scalar))
        (local.set $j (i32.add (local.get $j) (i32.const 1)))
        (br $tail)))))
