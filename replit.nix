{ pkgs }: {
  deps = [
    pkgs.bash
    pkgs.rustc
    pkgs.pkg-config
    pkgs.openssl
    pkgs.libxcrypt
    pkgs.libiconv
    pkgs.cargo
    pkgs.nvidia-docker
    pkgs.docker
    pkgs.python39Packages.streamlit
    pkgs.python39Packages.pdfplumber
    pkgs.python39Packages.requests
    pkgs.python39Packages.beautifulsoup4
    pkgs.python39Packages.trafilatura
    pkgs.python39Packages.langchain
    pkgs.python39Packages.nltk
    pkgs.python39Packages.pytorch
    pkgs.python39Packages.transformers
    pkgs.python39Packages.pydantic
    pkgs.python39Packages.orjson
    pkgs.python39Packages.langchain-community
    pkgs.python39Packages.sentence-transformers
    (pkgs.python39Packages.cryptography.overrideAttrs (oldAttrs: rec {
      version = "41.0.3";  # Pin to a compatible version
      sha256 = "0z5yxa702xk0r4ljcmz91fqxvdd1c72ib2acqnxsjv7w5zxdkg1v"; # Add correct sha256 for the specified version
    }))
  ];
}