"""Example of loading medications."""

import psycop_feature_generation.loaders.raw.load_medications as m

if __name__ == "__main__":
    df = m.first_gen_antipsychotics(n_rows=1000)
