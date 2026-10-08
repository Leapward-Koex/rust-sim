// Binary64 arithmetic and the original ChaCha12 stream are compatibility
// requirements. Do not build this program with fast-math or contraction.
#pragma OPENCL EXTENSION cl_khr_fp64 : enable
#pragma OPENCL FP_CONTRACT OFF

#define QR(a,b,c,d) a += b; d = rotate(d ^ a, 16u); c += d; b = rotate(b ^ c, 12u); a += b; d = rotate(d ^ a, 8u); c += d; b = rotate(b ^ c, 7u)

inline void chacha12(global const uint *key, ulong counter, ulong stream,
                     private uint *out) {
    uint x0=0x61707865u, x1=0x3320646eu, x2=0x79622d32u, x3=0x6b206574u;
    uint x4=key[0], x5=key[1], x6=key[2], x7=key[3];
    uint x8=key[4], x9=key[5], x10=key[6], x11=key[7];
    uint x12=(uint)counter, x13=(uint)(counter>>32);
    uint x14=(uint)stream, x15=(uint)(stream>>32);
    for (uint i=0; i<6; ++i) {
        QR(x0,x4,x8,x12); QR(x1,x5,x9,x13); QR(x2,x6,x10,x14); QR(x3,x7,x11,x15);
        QR(x0,x5,x10,x15); QR(x1,x6,x11,x12); QR(x2,x7,x8,x13); QR(x3,x4,x9,x14);
    }
    out[0]=x0+0x61707865u; out[1]=x1+0x3320646eu;
    out[2]=x2+0x79622d32u; out[3]=x3+0x6b206574u;
    out[4]=x4+key[0]; out[5]=x5+key[1]; out[6]=x6+key[2]; out[7]=x7+key[3];
    out[8]=x8+key[4]; out[9]=x9+key[5]; out[10]=x10+key[6]; out[11]=x11+key[7];
    out[12]=x12+(uint)counter; out[13]=x13+(uint)(counter>>32);
    out[14]=x14+(uint)stream; out[15]=x15+(uint)(stream>>32);
}
inline uint random_word(global const uint *key, ulong stream, ulong pos,
                        private ulong *cached_block, private uint *cache) {
    ulong block=pos>>4;
    if (*cached_block != block) {
        chacha12(key, block, stream, cache);
        *cached_block=block;
    }
    return cache[pos & 15ul];
}
inline double uniform_at(global const uint *key, ulong stream, ulong pos,
                         private ulong *cached_block, private uint *cache) {
    ulong lo=(ulong)random_word(key, stream, pos, cached_block, cache);
    ulong hi=(ulong)random_word(key, stream, pos+1ul, cached_block, cache);
    return (double)(((hi<<32)|lo)>>11) * 0x1.0p-53;
}

kernel void fitness(global const uchar *genes, global double *weights,
                    global const ulong *counts, global const uint *failed, ulong stride, ulong loci,
                    ulong n, uint first, double c_ch, double c_res) {
    ulong flat=get_global_id(0), repeat=flat/stride, i=flat%stride;
    if (failed[repeat]) return;
    ulong count=first ? counts[repeat] : n;
    if (i >= count) return;
    uint c=0, r=0;
    for (ulong j=0; j<loci; ++j) {
        uchar g=genes[(repeat*stride+i)*loci+j];
        c += g & 1u; r += (g>>1) & 1u;
    }
    weights[flat]=(1.0-c_ch*(double)c)+(1.0-c_res*(double)r)/2.0;
}

// A parallel scan changes floating-point addition order. One work item per
// repeat preserves the CPU prefix exactly; repeats execute independently.
kernel void prefix(global const double *weights, global double *cumulative,
                   global const ulong *counts, global uint *failed,
                   ulong stride, ulong n, uint first) {
    ulong repeat=get_global_id(0), base=repeat*stride;
    if (failed[repeat]) return;
    ulong count=first ? counts[repeat] : n;
    double total=0.0;
    for (ulong i=0; i<count; ++i) {
        total += weights[base+i];
        cumulative[base+i]=total;
    }
    if (!(total>0.0) || !isfinite(total)) failed[repeat]=1u;
}

kernel void offspring(global const uchar *genes, global const long *mating,
                      global const double *weights, global const double *cumulative,
                      global uchar *next_genes, global long *next_mating,
                      global double *next_fitness, global const ulong *counts,
                      global const uint *failed, global const uint *keys,
                      global const ulong *streams, global const ulong *positions,
                      ulong stride, ulong loci, ulong n, uint first,
                      ulong generation_words, double m_ch, double m_re) {
    ulong flat=get_global_id(0), repeat=flat/n, i=flat%n;
    if (failed[repeat]) return;
    ulong base=repeat*stride, count=first ? counts[repeat] : n;
    ulong start=positions[repeat]+generation_words;
    ulong cache_block=~0ul;
    uint cache[16];
    double u=uniform_at(keys+repeat*8ul, streams[repeat], start+2ul*i, &cache_block, cache);
    double value=u*cumulative[base+count-1ul];
    ulong lo=0, hi=count-1ul;
    while (lo<hi) {
        ulong mid=(lo+hi)/2ul;
        if (value<cumulative[base+mid]) hi=mid; else lo=mid+1ul;
    }
    ulong parent=base+lo, child=base+i;
    next_mating[child]=mating[parent];
    next_fitness[child]=weights[parent];
    ulong mutation=start+2ul*n+4ul*i*loci;
    for (ulong j=0; j<loci; ++j) {
        uchar g=genes[parent*loci+j];
        if (uniform_at(keys+repeat*8ul, streams[repeat], mutation+4ul*j,
                       &cache_block, cache)<=m_ch) g ^= 1u;
        if (uniform_at(keys+repeat*8ul, streams[repeat], mutation+4ul*j+2ul,
                       &cache_block, cache)<=m_re) g ^= 2u;
        next_genes[child*loci+j]=g;
    }
}

// Used by hardware tests to verify odd offsets and 16-word block boundaries.
kernel void rng_probe(global const uint *keys, global const ulong *streams,
                      global const ulong *positions, global double *out) {
    ulong i=get_global_id(0), cache_block=~0ul;
    uint cache[16];
    out[i]=uniform_at(keys, streams[0], positions[0]+2ul*i, &cache_block, cache);
}
