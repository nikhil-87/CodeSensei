"""Regex parser — coverage across JS/TS/Java/Go/Rust."""
from __future__ import annotations

import pytest

from engine.parsers.base import ParseInput
from engine.parsers.regex_parser import RegexParser


@pytest.fixture
def parser() -> RegexParser:
    return RegexParser()


def test_javascript_extracts_imports_and_functions(parser: RegexParser) -> None:
    src = """\
import { foo } from './utils';
import bar from "lodash";
const helper = require('./helper');

export function doThing(x) {
    if (x > 0 && x < 10) return x;
    return null;
}

export class Service {}
"""
    out = parser.parse(
        ParseInput(relative_path="a.js", source=src, language="javascript")
    )
    names = {s.name for s in out.symbols}
    assert "doThing" in names
    assert "Service" in names
    modules = {imp.module for imp in out.imports}
    assert "./utils" in modules
    assert "lodash" in modules
    assert "./helper" in modules
    assert out.cyclomatic > 1


def test_typescript_extracts_interfaces_and_types(parser: RegexParser) -> None:
    src = """\
import type { User } from "./user";
import { fetchAll } from "./api";

export interface Greeter { greet(name: string): string; }
export type Maybe<T> = T | null;

export class Impl implements Greeter {
    greet(name: string): string {
        if (!name) {
            return "hi";
        }
        return `hi ${name}`;
    }
}
"""
    out = parser.parse(
        ParseInput(relative_path="a.ts", source=src, language="typescript")
    )
    names = {s.name for s in out.symbols}
    assert "Greeter" in names
    assert "Impl" in names
    assert "Maybe" in names
    assert "./user" in {imp.module for imp in out.imports}


def test_go_extracts_imports(parser: RegexParser) -> None:
    src = """\
package main

import (
    "fmt"
    "github.com/foo/bar"
)

func Hello() string {
    if true {
        return "hi"
    }
    return ""
}

type Greeter struct{}
type Sayer interface{ Say() string }
"""
    out = parser.parse(
        ParseInput(relative_path="a.go", source=src, language="go")
    )
    modules = {imp.module for imp in out.imports}
    assert "fmt" in modules
    assert "github.com/foo/bar" in modules
    names = {s.name for s in out.symbols}
    assert "Hello" in names
    assert {"Greeter", "Sayer"} <= names


def test_rust_extracts_uses_and_fns(parser: RegexParser) -> None:
    src = """\
use std::collections::HashMap;
use crate::utils::helper;

pub fn calculate(x: i32) -> i32 {
    if x > 0 && x < 10 { x } else { -1 }
}

pub struct Counter;
pub trait Renderable {}
"""
    out = parser.parse(
        ParseInput(relative_path="a.rs", source=src, language="rust")
    )
    names = {s.name for s in out.symbols}
    assert {"calculate", "Counter", "Renderable"} <= names
    assert any("collections" in imp.module for imp in out.imports)


def test_unknown_language_returns_empty(parser: RegexParser) -> None:
    out = parser.parse(
        ParseInput(relative_path="a.zz", source="abc", language="zzlang")
    )
    assert out.symbols == ()
    assert out.imports == ()
