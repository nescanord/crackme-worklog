NecrumWin (Reezli challenge) - README operativo
===============================================

Objetivo:
- recuperar una password valida
- o producir un bypass estable

Estado actual:
- la linea activa ya no es solo `DEADC0DE` ni `xabort`
- el frente real es una cadena de trampolines tardios

Parches tardios productivos:
- `0x1e0ae4c -> ret`
- `0x1203bb4 -> add rsp, 8 ; ret`
- `0x5a6c54a -> xor cx, cx ; nop`
- `0x55efa2 -> ret`
- `0x5898a23 -> ret`
- `0x55da697 -> add rsp, 8 ; ret`

Progresion observada:
- `crackme+0x1e0ae4c`
- `crackme+0x5a6c54a`
- `0x800000023`
- `crackme+0x446f267`

Interpretacion:
- el bypass parece una cadena de stubs/trampolines
- ya no parece un unico branch final

Fuente de verdad:
- `README.md`
- `findings.md`
- `timeline.md`
- `next-steps.md`
- `notes/memoria_canonica.txt`
