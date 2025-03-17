{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.11";
    flake-utils.url = "github:numtide/flake-utils";
    pre-commit-hooks.url = "github:cachix/git-hooks.nix";
    v-utils.url = "github:valeratrades/.github";
  };

  outputs =
    { self
    , nixpkgs
    , flake-utils
    , pre-commit-hooks
    , v-utils
    ,
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = import nixpkgs {
          inherit system;
          allowUnfree = true;
        };

        pre-commit-check = pre-commit-hooks.lib.${system}.run (v-utils.files.preCommit { inherit pkgs; });
        pname = "translate_infrequent";
        stdenv = pkgs.stdenvAdapters.useMoldLinker pkgs.stdenv;

        workflowContents = v-utils.ci {
          inherit pkgs;
          lastSupportedVersion = "";
          jobsErrors = [ ];
          jobsWarnings = [ "tokei" ];
        };
        readme = v-utils.readme-fw {
          inherit pkgs pname;
          lastSupportedVersion = "python-3.12.9";
          rootDir = ./.;
          licenses = [
            {
              name = "Blue Oak 1.0.0";
              outPath = "LICENSE";
            }
          ];
          badges = [
            "msrv"
            "loc"
            "ci"
          ];
        };
        pythonPkgs = pkgs.python3.withPackages (ps: with ps; [
          icecream
					wordfreq
					translatepy
					jellyfish
					unicodedata2
        ]);
      in
      {
				packages.default = pkgs.writeShellScriptBin "run-python" ''
						export PYTHONPATH="${self}"
						${pythonPkgs}/bin/python -m src "$@"
						'';

        devShells.default =
          with pkgs;
          mkShell {
            inherit stdenv;
            shellHook =
              pre-commit-check.shellHook
              + ''
                mkdir -p ./.github/workflows
                rm -f ./.github/workflows/errors.yml; cp ${workflowContents.errors} ./.github/workflows/errors.yml
                rm -f ./.github/workflows/warnings.yml; cp ${workflowContents.warnings} ./.github/workflows/warnings.yml

                cp -f ${v-utils.files.licenses.blue_oak} ./LICENSE

                cargo -Zscript -q ${v-utils.hooks.appendCustom} ./.git/hooks/pre-commit
                cp -f ${(v-utils.hooks.treefmt) { inherit pkgs; }} ./.treefmt.toml
                cp -f ${(v-utils.hooks.preCommit) { inherit pkgs pname; }} ./.git/hooks/custom.sh

                cp -f ${
                  (v-utils.files.gitignore {
                    inherit pkgs;
                    langs = [ "py" ];
                  })
                } ./.gitignore
                cp -f ${(v-utils.files.python.ruff { inherit pkgs; })} ./ruff.toml

                cp -f ${readme} ./README.md
              '';

            packages = [
              mold-wrapped
              pythonPkgs
            ] ++ pre-commit-check.enabledPackages;
          };
      }
    );
}
