/*===========================================================================
  Copyright (C) 2018 by the Okapi Framework contributors
-----------------------------------------------------------------------------
  Licensed under the Apache License, Version 2.0 (the "License");
  you may not use this file except in compliance with the License.
  You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

  Unless required by applicable law or agreed to in writing, software
  distributed under the License is distributed on an "AS IS" BASIS,
  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
  See the License for the specific language governing permissions and
  limitations under the License.
===========================================================================*/

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;

import net.sf.okapi.common.Event;
import net.sf.okapi.common.LocaleId;
import net.sf.okapi.common.filterwriter.XLIFFWriter;
import net.sf.okapi.common.resource.RawDocument;
import net.sf.okapi.filters.html.HtmlFilter;
import net.sf.okapi.steps.wordcount.WordCountStep;
import net.sf.okapi.steps.wordcount.WordCounter;

public class Main {

	private static final LocaleId TARGET_LOCALE = LocaleId.FRENCH;
	private static final LocaleId SOURCE_LOCALE = LocaleId.ENGLISH;
	private static final String ENCODING = "UTF-8";
	private static final String INPUT_FILE = "home.htm";
	private static final String OUT_ROOT = new File(Main.class.getResource(INPUT_FILE).getPath()).getParent();

	public static void main (String[] args) {

		try (InputStream fis = Main.class.getResourceAsStream(INPUT_FILE);
				FileOutputStream fos = new FileOutputStream(new File(OUT_ROOT, "home.xliff"));
				RawDocument doc = new RawDocument(fis, ENCODING, SOURCE_LOCALE, TARGET_LOCALE);
				HtmlFilter filter = new HtmlFilter();
				XLIFFWriter writer = new XLIFFWriter()) {

			filter.open(doc, true);
			writer.setOutput(fos);

			WordCountStep wc = new WordCountStep();

			long wordCount = filter.stream()
					.peek(writer::handleEvent) // write to XLIFF
					.map(wc::handleEvent)
					.filter(Event::isTextUnit) // if event.isTextUnit()
					.map(Event::getTextUnit)   // get the TextUnit part
					.mapToLong(WordCounter::getCount) // and get the word count annotation
					.sum(); // sum of word counts for all text units

			System.out.println("Total word count : " + wordCount);

		} catch (IOException e) {
			e.printStackTrace();
		}

	}
}
