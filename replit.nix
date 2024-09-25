{ pkgs }: {
  deps = [
    pkgs.rustc
    pkgs.pkg-config
    pkgs.openssl
    pkgs.cargo
    pkgs.libiconv
    pkgs.libxcrypt
    pkgs.streamlit
    pkgs.openssh
    pkgs.bash
    pkgs.postgresql
    pkgs.python3Packages.pdfplumber
    pkgs.python3Packages.beautifulsoup4
    pkgs.python3Packages.pip
    pkgs.python3Packages.requests
    pkgs.python3Packages.trafilatura
    pkgs.python3Packages.nltk
    pkgs.python3Packages.pytorch
    pkgs.python3Packages.transformers
    pkgs.python3Packages.pydantic
    pkgs.python3Packages.orjson
  ];
}