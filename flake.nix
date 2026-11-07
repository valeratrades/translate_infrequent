{
  inputs = {
    v_flakes.url = "github:valeratrades/v_flakes?ref=v1.6";
  };

  outputs =
    { self, v_flakes }:
    let
      inherit (v_flakes) flake-utils pre-commit-hooks;
      pname = "translate_infrequent";
    in
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = import v_flakes.default_nixpkgs { inherit system; };
        rust = v_flakes.rs.default_nightly system;
        pre-commit-check = pre-commit-hooks.lib.${system}.run (v_flakes.files.preCommit { inherit pkgs; });

        build_rust = v_flakes.rs.build_nightly system;
        rustPlatform = pkgs.makeRustPlatform { rustc = build_rust; cargo = build_rust; };
        askLlmPy = pkgs.python312.pkgs.buildPythonPackage {
          pname = "ask_llm_py";
          version = "0.1.0";
          format = "pyproject";
          src = ./ask_llm_py;
          cargoDeps = rustPlatform.importCargoLock { lockFile = ./ask_llm_py/Cargo.lock; };
          nativeBuildInputs = [
            rustPlatform.cargoSetupHook
            (rustPlatform.maturinBuildHook.overrideAttrs { propagatedBuildInputs = [ pkgs.maturin build_rust ]; }) # nixpkgs' propagates stable cargo/rustc, ahead of ours on PATH
          ];
          RUSTC = "${build_rust}/bin/rustc";
          CARGO = "${build_rust}/bin/cargo";
        };

        pythonPkgs = pkgs.python312.withPackages (ps: with ps; [
          askLlmPy
          icecream
          wordfreq
          translatepy
          jellyfish
          unicodedata2
          phonemizer
          simplemma
          numpy
        ]);
        pythonVersion = "python-${pythonPkgs.python.pythonVersion}";

        github = v_flakes.github {
          inherit pkgs pname;
          rs = { inherit rust; }; # `enable` runs append_custom.rs through cargo, which github only reaches via `rs`
          langs = [ "py" ]; # a non-null `rs` otherwise infers "rs" into the generated gitignore and CI defaults
          enable = true;
          lastSupportedVersion = pythonVersion;
          jobs.warnings.augment = [ "tokei" ];
          gitignore.extra = "ask_llm_py/target";
          publishCachix = { name = "valeratrades"; tags = true; };
        };
        readme = v_flakes.readme-fw {
          inherit pkgs pname;
          lastSupportedVersion = pythonVersion;
          rootDir = ./.;
          licenses = [{ license = v_flakes.files.licenses.blue_oak; }];
          badges = [ "msrv" "loc" "ci" ];
        };

        combined = v_flakes.utils.combine { inherit rust; modules = [ github readme ]; };
      in
      {
        packages.default = pkgs.writeShellScriptBin pname ''
          export PYTHONPATH="${self}:$PYTHONPATH"; exec ${pythonPkgs}/bin/python -m src "$@"
        '';

        devShells.default = pkgs.mkShell {
          shellHook =
            pre-commit-check.shellHook +
            combined.shellHook +
            ''
              cp -f ${(v_flakes.files.treefmt) { inherit pkgs; }} ./.treefmt.toml
              cp -f ${(v_flakes.files.python.ruff) { inherit pkgs; }} ./ruff.toml
            '';

          packages = [
            pythonPkgs
          ] ++ pre-commit-check.enabledPackages ++ combined.enabledPackages;
        };
      }
    );
}
