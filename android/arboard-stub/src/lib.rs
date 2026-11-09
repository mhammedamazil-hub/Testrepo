//! Android build shim: desktop arboard has no Android backend. All operations
//! fail explicitly; the host terminal still accepts normal text input/paste.
use std::borrow::Cow;
use std::fmt;

#[derive(Debug)]
pub struct Error;
impl fmt::Display for Error {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result { f.write_str("native clipboard is unavailable on Android") }
}
impl std::error::Error for Error {}
pub struct ImageData<'a> { pub width: usize, pub height: usize, pub bytes: Cow<'a, [u8]> }
pub struct Clipboard;
impl Clipboard {
    pub fn new() -> Result<Self, Error> { Err(Error) }
    pub fn get_text(&mut self) -> Result<String, Error> { Err(Error) }
    pub fn set_text<T: Into<String>>(&mut self, _: T) -> Result<(), Error> { Err(Error) }
    pub fn get_image(&mut self) -> Result<ImageData<'static>, Error> { Err(Error) }
    pub fn set_image(&mut self, _: ImageData<'_>) -> Result<(), Error> { Err(Error) }
}
