wit_bindgen::generate!({
    world: "wasiless",
    path: "wit",
    generate_all,
});

pub use exports::wasi;
